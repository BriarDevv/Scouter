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
    # Rate limiting defaults
    task_default_rate_limit="10/m",
    # Retry defaults
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Routing: separate queues for different workloads
    task_routes={
        "app.workers.tasks.task_enrich_lead": {"queue": "enrichment"},
        "app.workers.tasks.task_score_lead": {"queue": "scoring"},
        "app.workers.tasks.task_generate_draft": {"queue": "llm"},
        "app.workers.tasks.task_analyze_lead": {"queue": "llm"},
        "app.workers.tasks.task_review_lead": {"queue": "reviewer"},
        "app.workers.tasks.task_review_draft": {"queue": "reviewer"},
    },
    # Default queue for unmatched tasks
    task_default_queue="default",
)

celery_app.autodiscover_tasks(["app.workers"])
