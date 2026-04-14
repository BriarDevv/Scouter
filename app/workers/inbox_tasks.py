"""Celery tasks for inbound mail sync."""

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.inbox_tasks.task_sync_inbound_mail",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=60,
)
def task_sync_inbound_mail(self):
    """Periodic task: sync inbound mail if enabled."""
    from app.core.config import settings

    if not settings.MAIL_INBOUND_ENABLED:
        logger.debug("inbound_mail_sync_disabled")
        return {"status": "skipped", "reason": "inbound_mail_disabled"}

    try:
        from app.db.session import SessionLocal
        from app.services.inbox.inbound_mail_service import sync_inbound_messages

        with SessionLocal() as db:
            sync_run = sync_inbound_messages(db)
            return {
                "status": "ok",
                "sync_run_id": str(sync_run.id),
                "new_count": sync_run.new_count,
            }
    except Exception as exc:
        logger.error("task_sync_inbound_mail_error", error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
