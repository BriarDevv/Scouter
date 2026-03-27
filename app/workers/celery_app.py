from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "clawscout",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

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
    # Routing: separate queues for different workloads
    task_routes={
        "app.workers.tasks.task_enrich_lead": {"queue": "enrichment"},
        "app.workers.tasks.task_score_lead": {"queue": "scoring"},
        "app.workers.tasks.task_generate_draft": {"queue": "llm"},
        "app.workers.tasks.task_analyze_lead": {"queue": "llm"},
        "app.workers.tasks.task_review_lead": {"queue": "reviewer"},
        "app.workers.tasks.task_review_draft": {"queue": "reviewer"},
        "app.workers.tasks.task_review_inbound_message": {"queue": "reviewer"},
        "app.workers.tasks.task_review_reply_assistant_draft": {"queue": "reviewer"},
        "app.workers.tasks.task_crawl_territory": {"queue": "default"},
    },
    # Default queue for unmatched tasks
    task_default_queue="default",
    # Beat schedule — periodic maintenance
    beat_schedule={
        "sweep-stale-tasks": {
            "task": "app.workers.janitor.task_sweep_stale",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
import app.workers.janitor  # noqa: F401 — register janitor beat task
