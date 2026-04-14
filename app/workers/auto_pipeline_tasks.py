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
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=60,
)
def task_auto_process_new_leads(self):
    """Beat task: dispatch full pipeline for leads that are new and at least 10 minutes old.

    When no eligible leads are present and `auto_replenish_enabled` is set,
    this dispatches a crawl for the least-recently-crawled active,
    non-saturated territory. Keeps the pipeline fed outside the cron-scheduled
    Mon/Thu 8am crawl window.
    """
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
            if getattr(settings, "auto_replenish_enabled", False):
                replenish_result = _trigger_auto_replenish(db)
                if replenish_result is not None:
                    return replenish_result
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


def _trigger_auto_replenish(db) -> dict | None:
    """Dispatch a crawl for the least-recently-crawled active territory.

    Returns the beat-task result payload if a crawl was dispatched, or None
    if no eligible territory exists (caller falls through to the no-leads
    payload).
    """
    from sqlalchemy import asc, nulls_first

    from app.models.territory import Territory

    next_territory = (
        db.query(Territory)
        .filter(Territory.is_active.is_(True), Territory.is_saturated.is_(False))
        .order_by(nulls_first(asc(Territory.last_crawled_at)))
        .first()
    )
    if next_territory is None:
        logger.info("auto_replenish_no_territory_available")
        return None

    # Import lazily so the module stays importable without celery task
    # registry in test contexts.
    from app.workers.crawl_tasks import task_crawl_territory

    try:
        task_crawl_territory.delay(str(next_territory.id))
    except Exception as exc:
        logger.warning(
            "auto_replenish_dispatch_failed",
            territory_id=str(next_territory.id),
            error=str(exc),
        )
        return None

    logger.info(
        "auto_replenish_triggered",
        territory_id=str(next_territory.id),
        territory_name=next_territory.name,
        last_crawled_at=str(next_territory.last_crawled_at),
    )
    return {"status": "replenish_triggered", "territory_id": str(next_territory.id)}
