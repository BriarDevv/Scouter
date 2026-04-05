"""Batch review tasks — threshold check and manual trigger."""

from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.batch_review_tasks.task_check_batch_review",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def task_check_batch_review(self, correlation_id: str | None = None) -> dict:
    """Check if batch review thresholds are met and trigger if so."""
    try:
        with SessionLocal() as db:
            from app.services.pipeline.batch_review_service import check_review_threshold

            trigger = check_review_threshold(db)
            if not trigger:
                return {"status": "skipped", "reason": "threshold_not_met"}

            logger.info("batch_review_threshold_met", trigger=trigger)

            from app.services.pipeline.batch_review_service import generate_batch_review

            review = generate_batch_review(db, trigger_reason=trigger)
            return {
                "status": review.status,
                "review_id": str(review.id),
                "trigger": trigger,
                "batch_size": review.batch_size,
                "proposals_count": len(review.proposals),
            }
    except Exception as exc:
        logger.error("batch_review_check_failed", error=str(exc))
        return {"status": "error", "error": str(exc)[:500]}


@celery_app.task(
    name="app.workers.batch_review_tasks.task_generate_batch_review_manual",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def task_generate_batch_review_manual(self, correlation_id: str | None = None) -> dict:
    """Force-trigger a batch review regardless of thresholds."""
    try:
        with SessionLocal() as db:
            from app.services.pipeline.batch_review_service import generate_batch_review

            review = generate_batch_review(db, trigger_reason="manual")
            return {
                "status": review.status,
                "review_id": str(review.id),
                "batch_size": review.batch_size,
                "proposals_count": len(review.proposals),
            }
    except Exception as exc:
        logger.error("batch_review_manual_failed", error=str(exc))
        return {"status": "error", "error": str(exc)[:500]}
