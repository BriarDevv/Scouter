"""Periodic janitor — marks stale tasks and pipelines as failed so the system recovers."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.task_tracking import PipelineRun, TaskRun
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

STALE_THRESHOLD = timedelta(minutes=10)
PIPELINE_STALE_THRESHOLD = timedelta(minutes=15)
ACTIVE_STATUSES = ("running", "queued", "retrying", "stopping")


def sweep_stale_tasks(session_factory=None) -> dict:
    """Find tasks and pipelines stuck in active status and mark them failed."""
    cutoff = datetime.now(UTC) - STALE_THRESHOLD
    pipeline_cutoff = datetime.now(UTC) - PIPELINE_STALE_THRESHOLD
    factory = session_factory or SessionLocal

    with factory() as db:
        # Sweep stale TaskRuns
        stale = db.execute(
            select(TaskRun).where(
                TaskRun.status.in_(ACTIVE_STATUSES),
                TaskRun.updated_at < cutoff,
            )
        ).scalars().all()

        task_count = 0
        for task_run in stale:
            task_run.status = "failed"
            task_run.error = (
                f"Stale: no progress for "
                f">{STALE_THRESHOLD.total_seconds() / 60:.0f} min "
                f"— marked failed by janitor"
            )
            task_run.finished_at = datetime.now(UTC)
            task_count += 1
            logger.warning(
                "janitor_marked_stale_task",
                task_id=task_run.task_id,
                task_name=task_run.task_name,
                last_updated=str(task_run.updated_at),
            )

        # Sweep stale PipelineRuns
        stale_pipelines = db.execute(
            select(PipelineRun).where(
                PipelineRun.status.in_(ACTIVE_STATUSES),
                PipelineRun.updated_at < pipeline_cutoff,
            )
        ).scalars().all()

        pipeline_count = 0
        for pipeline_run in stale_pipelines:
            pipeline_run.status = "failed"
            pipeline_run.error = (
                f"Stale: no progress for "
                f">{PIPELINE_STALE_THRESHOLD.total_seconds() / 60:.0f} min "
                f"— marked failed by janitor"
            )
            pipeline_run.finished_at = datetime.now(UTC)
            pipeline_count += 1
            logger.warning(
                "janitor_marked_stale_pipeline",
                pipeline_run_id=str(pipeline_run.id),
                lead_id=str(pipeline_run.lead_id),
                current_step=pipeline_run.current_step,
                last_updated=str(pipeline_run.updated_at),
            )

        if task_count or pipeline_count:
            db.commit()

    result = {"tasks_failed": task_count, "pipelines_failed": pipeline_count}
    logger.info("janitor_sweep_done", **result)
    return result


@celery_app.task(name="app.workers.janitor.task_sweep_stale")
def task_sweep_stale() -> dict:
    """Celery-wrapped janitor for use with celery beat."""
    return sweep_stale_tasks()
