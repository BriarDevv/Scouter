"""Celery beat task: auto-dispatch full pipeline for new leads."""

from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

_BATCH_CAP = 20
_MIN_AGE_MINUTES = 10


@celery_app.task(
    name="app.workers.auto_pipeline_tasks.task_auto_process_new_leads",
    bind=True,
    max_retries=0,
)
def task_auto_process_new_leads(self):
    """Beat task: dispatch full pipeline for leads that are new and at least 10 minutes old."""
    from app.models.lead import Lead
    from app.models.settings import OperationalSettings
    from app.workers.pipeline_tasks import task_full_pipeline

    with SessionLocal() as db:
        settings = db.get(OperationalSettings, 1)
        if settings is None or not settings.auto_pipeline_enabled:
            logger.info("auto_pipeline_disabled_skipping")
            return {"status": "skipped", "reason": "auto_pipeline_disabled"}

        from app.workers.metrics import get_queue_depths

        depths = get_queue_depths()
        if depths.get("active", 0) + depths.get("reserved", 0) > 50:
            logger.info("auto_pipeline_skipped_backpressure", queue_depth=depths)
            return {"status": "skipped", "reason": "backpressure", "queue_depth": depths}

        cutoff = datetime.now(UTC) - timedelta(minutes=_MIN_AGE_MINUTES)
        leads = (
            db.query(Lead)
            .filter(Lead.status == "new", Lead.created_at < cutoff)
            .limit(_BATCH_CAP)
            .all()
        )

        if not leads:
            logger.info("auto_pipeline_no_eligible_leads")
            return {"status": "ok", "dispatched": 0}

        dispatched = 0
        for lead in leads:
            try:
                task_full_pipeline.delay(str(lead.id))
                dispatched += 1
            except Exception as exc:
                logger.warning(
                    "auto_pipeline_dispatch_failed",
                    lead_id=str(lead.id),
                    error=str(exc),
                )

        logger.info("auto_pipeline_dispatched", count=dispatched)
        return {"status": "ok", "dispatched": dispatched}
