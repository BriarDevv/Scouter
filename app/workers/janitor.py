"""Periodic janitor — marks stale tasks as failed so the system recovers."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.task_tracking import TaskRun
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

STALE_THRESHOLD = timedelta(minutes=10)
ACTIVE_STATUSES = ("running", "queued", "retrying")


def sweep_stale_tasks(session_factory=None) -> dict:
    """Find tasks stuck in active status > STALE_THRESHOLD and mark them failed."""
    cutoff = datetime.now(UTC) - STALE_THRESHOLD
    factory = session_factory or SessionLocal

    with factory() as db:
        stale = db.execute(
            select(TaskRun).where(
                TaskRun.status.in_(ACTIVE_STATUSES),
                TaskRun.updated_at < cutoff,
            )
        ).scalars().all()

        count = 0
        for task_run in stale:
            task_run.status = "failed"
            task_run.error = f"Stale: no progress for >{STALE_THRESHOLD.total_seconds() / 60:.0f} min — marked failed by janitor"
            task_run.finished_at = datetime.now(UTC)
            count += 1
            logger.warning(
                "janitor_marked_stale",
                task_id=task_run.task_id,
                task_name=task_run.task_name,
                last_updated=str(task_run.updated_at),
            )

        if count:
            db.commit()

    result = {"marked_failed": count}
    logger.info("janitor_sweep_done", **result)
    return result


@celery_app.task(name="app.workers.janitor.task_sweep_stale")
def task_sweep_stale() -> dict:
    """Celery-wrapped janitor for use with celery beat."""
    return sweep_stale_tasks()
