from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "scouter",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Queue routing: separate queues for different workloads (full resource mode)
_TASK_ROUTES_FULL = {
    "app.workers.tasks.task_enrich_lead": {"queue": "enrichment"},
    "app.workers.tasks.task_score_lead": {"queue": "scoring"},
    "app.workers.tasks.task_generate_draft": {"queue": "llm"},
    "app.workers.tasks.task_analyze_lead": {"queue": "llm"},
    "app.workers.tasks.task_review_lead": {"queue": "reviewer"},
    "app.workers.tasks.task_review_draft": {"queue": "reviewer"},
    "app.workers.tasks.task_review_inbound_message": {"queue": "reviewer"},
    "app.workers.tasks.task_review_reply_assistant_draft": {"queue": "reviewer"},
    "app.workers.tasks.task_crawl_territory": {"queue": "default"},
    "app.workers.tasks.task_research_lead": {"queue": "research"},
    "app.workers.brief_tasks.task_generate_brief": {"queue": "llm"},
    "app.workers.brief_tasks.task_review_brief": {"queue": "reviewer"},
}

# Low resource mode: DB setting overrides env var
def _resolve_low_resource() -> bool:
    """Check DB for low_resource_mode override, fall back to env var."""
    try:
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            from app.models.settings import OperationalSettings
            row = db.get(OperationalSettings, 1)
            if row and row.low_resource_mode is not None:
                return row.low_resource_mode
    except Exception:
        pass  # DB not available at startup — use env
    return settings.LOW_RESOURCE_MODE


_low_resource = _resolve_low_resource()

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    # No global rate limit; per-task limits if needed
    task_default_rate_limit=None,
    # Retry defaults
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Timeouts — prevent tasks from hanging indefinitely
    task_soft_time_limit=300,   # 5 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=360,        # 6 min hard kill
    # Routing: merge all queues in low resource mode
    task_routes={} if _low_resource else _TASK_ROUTES_FULL,
    # Default queue for unmatched tasks
    task_default_queue="default",
    # Concurrency: 1 worker in low resource mode to avoid loading multiple models
    worker_concurrency=1 if _low_resource else None,
    # Worker stability — prevent memory leaks from long-running processes
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1 if _low_resource else 2,
    # Beat schedule — periodic maintenance
    beat_schedule={
        "sweep-stale-tasks": {
            "task": "app.workers.janitor.task_sweep_stale",
            "schedule": 300.0,  # every 5 minutes
        },
        "weekly-ai-report": {
            "task": "app.workers.weekly_tasks.task_weekly_report",
            "schedule": crontab(day_of_week=0, hour=20, minute=0),
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
import app.workers.batch_tasks  # noqa: E402, F401 — register batch tasks
import app.workers.brief_tasks  # noqa: E402, F401 — register brief tasks
import app.workers.crawl_tasks  # noqa: E402, F401 — register crawl tasks
import app.workers.janitor  # noqa: E402, F401 — register janitor beat task
import app.workers.pipeline_tasks  # noqa: E402, F401 — register pipeline tasks
import app.workers.research_tasks  # noqa: E402, F401 — register research tasks
import app.workers.review_tasks  # noqa: E402, F401 — register review tasks
import app.workers.weekly_tasks  # noqa: E402, F401 — register weekly report beat task
