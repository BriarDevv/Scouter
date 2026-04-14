"""Composed sweep_stale_tasks — orchestrates every individual sweep in one DB session."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.task_tracking import PipelineRun, TaskRun
from app.services.notifications.notification_emitter import on_repeated_failures
from app.workers.janitor.stale import (
    ACTIVE_STATUSES,
    MAX_PIPELINE_RETRIES,
    PIPELINE_STALE_THRESHOLD,
    STALE_THRESHOLD,
    _auto_resume_pipeline,
    _check_pipeline_inactive,
    sweep_orphan_pipelines,
)
from app.workers.janitor.zombies import (
    sweep_stuck_research_reports,
    sweep_zombie_leads,
)

logger = get_logger(__name__)


def sweep_stale_tasks(session_factory=None) -> dict:
    """Find tasks and pipelines stuck in active status and mark them failed."""
    cutoff = datetime.now(UTC) - STALE_THRESHOLD
    pipeline_cutoff = datetime.now(UTC) - PIPELINE_STALE_THRESHOLD
    factory = session_factory or SessionLocal

    with factory() as db:
        # Sweep stale TaskRuns
        stale = (
            db.execute(
                select(TaskRun).where(
                    TaskRun.status.in_(ACTIVE_STATUSES),
                    TaskRun.updated_at < cutoff,
                )
            )
            .scalars()
            .all()
        )

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
        stale_pipelines = (
            db.execute(
                select(PipelineRun).where(
                    PipelineRun.status.in_(ACTIVE_STATUSES),
                    PipelineRun.updated_at < pipeline_cutoff,
                )
            )
            .scalars()
            .all()
        )

        pipeline_count = 0
        resumed_count = 0
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
            if _auto_resume_pipeline(pipeline_run):
                resumed_count += 1

        orphan_count = sweep_orphan_pipelines(db)

        # Attempt auto-resume for freshly-orphaned pipelines too.
        orphan_resumed = 0
        orphan_pipelines = (
            db.execute(
                select(PipelineRun).where(
                    PipelineRun.status == "failed",
                    PipelineRun.error.like("%orphaned%"),
                    PipelineRun.retry_count < MAX_PIPELINE_RETRIES,
                    PipelineRun.finished_at >= datetime.now(UTC) - timedelta(seconds=5),
                )
            )
            .scalars()
            .all()
        )
        for pipeline_run in orphan_pipelines:
            if _auto_resume_pipeline(pipeline_run):
                orphan_resumed += 1

        # Sweep stuck BatchReviews (generating/reviewing for >10 min).
        batch_review_count = 0
        try:
            from sqlalchemy import inspect as sa_inspect

            if sa_inspect(db.bind).has_table("batch_reviews"):
                from app.models.batch_review import BatchReview

                batch_review_cutoff = datetime.now(UTC) - timedelta(minutes=10)
                stuck_reviews = (
                    db.execute(
                        select(BatchReview).where(
                            BatchReview.status.in_(["generating", "reviewing"]),
                            BatchReview.updated_at < batch_review_cutoff,
                        )
                    )
                    .scalars()
                    .all()
                )
                for review in stuck_reviews:
                    old_status = review.status
                    review.status = "failed"
                    review.reviewer_notes = (
                        f"Stuck in '{old_status}' for >10 min — marked failed by janitor"
                    )
                    batch_review_count += 1
                    logger.warning(
                        "janitor_marked_stale_batch_review",
                        review_id=str(review.id),
                        previous_status=old_status,
                    )
        except Exception as exc:
            logger.debug("janitor_batch_review_sweep_failed", error=str(exc))

        research_report_count = sweep_stuck_research_reports(db)
        zombie_result = sweep_zombie_leads(db)
        _check_pipeline_inactive(db)

        if (
            task_count
            or pipeline_count
            or orphan_count
            or batch_review_count
            or research_report_count
        ):
            db.commit()

        if task_count > 3:
            total_stale = task_count + pipeline_count + orphan_count
            on_repeated_failures(
                db,
                failure_type="pipeline_health",
                count=total_stale,
                detail=(
                    f"Janitor sweep: {task_count} stale tasks, "
                    f"{pipeline_count} stale pipelines, "
                    f"{orphan_count} orphaned pipelines marked failed."
                ),
            )

    result = {
        "tasks_failed": task_count,
        "pipelines_failed": pipeline_count,
        "pipelines_resumed": resumed_count + orphan_resumed,
        "orphans_failed": orphan_count,
        "batch_reviews_failed": batch_review_count,
        "research_reports_failed": research_report_count,
        "zombie_leads": zombie_result,
    }
    logger.info("janitor_sweep_done", **result)
    return result
