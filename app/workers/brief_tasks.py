"""Celery tasks for commercial brief generation."""

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.task_tracking_service import (
    bind_tracking_context,
    clear_tracking_context,
    mark_task_failed,
    mark_task_running,
    mark_task_succeeded,
)
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.brief_tasks.task_generate_brief",
    bind=True,
    max_retries=1,
    soft_time_limit=120,
    time_limit=150,
)
def task_generate_brief(
    self, lead_id: str, pipeline_run_id: str | None = None
):
    """Generate a commercial brief for a lead asynchronously."""
    lead_uuid = uuid.UUID(lead_id)
    pipeline_uuid = (
        uuid.UUID(pipeline_run_id) if pipeline_run_id else None
    )

    db = SessionLocal()
    try:
        bind_tracking_context(
            db,
            celery_task_id=self.request.id,
            task_name="generate_brief",
            lead_id=lead_uuid,
            pipeline_run_id=pipeline_uuid,
            queue="llm",
        )
        mark_task_running(db)

        from app.services.brief_service import generate_brief

        brief = generate_brief(db, lead_uuid)
        if brief and brief.status.value == "generated":
            mark_task_succeeded(
                db,
                result_summary=f"score={brief.opportunity_score}",
            )
            logger.info(
                "task_generate_brief_done",
                lead_id=lead_id,
                opportunity_score=brief.opportunity_score,
            )
        else:
            error_msg = (
                brief.error if brief else "Lead not found"
            )
            mark_task_failed(db, error=error_msg or "unknown")
            logger.warning(
                "task_generate_brief_failed",
                lead_id=lead_id,
                error=error_msg,
            )
    except Exception as exc:
        mark_task_failed(db, error=str(exc)[:500])
        logger.error(
            "task_generate_brief_error",
            lead_id=lead_id,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        clear_tracking_context()
        db.close()
