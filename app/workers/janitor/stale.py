"""Stale-task detection helpers — constants, retry classification, orphan sweep.

Used by app.workers.janitor.orchestrator.sweep_stale_tasks. Broken out so
the orchestrator stays focused on composition and each helper can be
unit-tested in isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger
from app.models.task_tracking import PipelineRun

logger = get_logger(__name__)

STALE_THRESHOLD = timedelta(minutes=10)
PIPELINE_STALE_THRESHOLD = timedelta(minutes=15)
ORPHAN_THRESHOLD = timedelta(minutes=30)
ACTIVE_STATUSES = ("running", "queued", "retrying", "stopping")

MAX_PIPELINE_RETRIES = 2

# Patterns that indicate a transient/retryable failure.
_RETRYABLE_PATTERNS = (
    "timeout",
    "timed out",
    "rate limit",
    "ratelimit",
    "429",
    "503",
    "502",
    "connection reset",
    "connection refused",
    "temporary",
    "overloaded",
    "llm error",
    "openai",
    "anthropic",
    "stale: no progress",
    "orphaned",
)


def _is_retryable_error(error: str | None) -> bool:
    """True if the error string suggests a transient/retryable failure."""
    if not error:
        return True  # No error info — assume transient (e.g. stale/orphaned)
    error_lower = error.lower()
    return any(pattern in error_lower for pattern in _RETRYABLE_PATTERNS)


def _auto_resume_pipeline(pipeline_run: PipelineRun) -> bool:
    """Attempt to auto-resume a failed pipeline run if retryable.

    Returns True if the pipeline was re-queued, False if left as permanently
    failed. Uses the canonical PIPELINE_STEP_CHAIN so the resume endpoint
    and this auto-resume logic never diverge.
    """
    if pipeline_run.retry_count >= MAX_PIPELINE_RETRIES:
        return False
    if not _is_retryable_error(pipeline_run.error):
        return False

    from app.workflows.step_chain import PIPELINE_STEP_CHAIN

    step = pipeline_run.current_step or "pipeline_dispatch"
    next_task_name = PIPELINE_STEP_CHAIN.get(step)
    if next_task_name is None:
        return False  # Terminal step, nothing to resume

    from app.workers import tasks as task_module

    task_fn = getattr(task_module, next_task_name, None)
    if task_fn is None:
        logger.error(
            "janitor_auto_resume_task_not_found",
            pipeline_run_id=str(pipeline_run.id),
            next_task=next_task_name,
        )
        return False

    pipeline_run.retry_count += 1
    pipeline_run.status = "running"
    pipeline_run.finished_at = None
    pipeline_run.error = None

    task_fn.delay(
        str(pipeline_run.lead_id),
        pipeline_run_id=str(pipeline_run.id),
        correlation_id=pipeline_run.correlation_id,
    )

    logger.info(
        "janitor_auto_resumed_pipeline",
        pipeline_run_id=str(pipeline_run.id),
        lead_id=str(pipeline_run.lead_id),
        retry_count=pipeline_run.retry_count,
        resumed_from=step,
        next_task=next_task_name,
    )
    return True


def sweep_orphan_pipelines(db) -> int:
    """Mark PipelineRuns stuck in 'running' with no activity for 30+ min as failed."""
    orphan_cutoff = datetime.now(UTC) - ORPHAN_THRESHOLD
    orphans = (
        db.execute(
            select(PipelineRun).where(
                PipelineRun.status == "running",
                PipelineRun.updated_at < orphan_cutoff,
            )
        )
        .scalars()
        .all()
    )

    count = 0
    for pipeline_run in orphans:
        pipeline_run.status = "failed"
        pipeline_run.error = "orphaned — no activity for 30 minutes"
        pipeline_run.finished_at = datetime.now(UTC)
        count += 1
        logger.warning(
            "janitor_marked_orphan_pipeline",
            pipeline_run_id=str(pipeline_run.id),
            lead_id=str(pipeline_run.lead_id),
            current_step=pipeline_run.current_step,
            last_updated=str(pipeline_run.updated_at),
        )
    return count


def _check_pipeline_inactive(db) -> None:
    """Emit an operator notification if the pipeline is idle despite pending leads."""
    from app.models.lead import Lead, LeadStatus

    cutoff = datetime.now(UTC) - timedelta(minutes=60)
    recent_runs = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.finished_at >= cutoff,
            PipelineRun.status == "succeeded",
        )
        .count()
    )
    pending_leads = db.query(Lead).filter(Lead.status == LeadStatus.NEW.value).count()

    if recent_runs == 0 and pending_leads > 0:
        from app.services.notifications.notification_emitter import _emit

        _emit(
            db,
            type="pipeline_inactive",
            category="system",
            severity="warning",
            title="Pipeline inactivo",
            message=(
                f"No hay pipeline runs en la ultima hora pero hay {pending_leads} leads pendientes."
            ),
            dedup_key="pipeline_inactive",
        )
