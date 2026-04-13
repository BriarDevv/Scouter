"""Periodic janitor — marks stale tasks and pipelines as failed so the system recovers."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.task_tracking import PipelineRun, TaskRun
from app.services.notifications.notification_emitter import on_repeated_failures
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

STALE_THRESHOLD = timedelta(minutes=10)
PIPELINE_STALE_THRESHOLD = timedelta(minutes=15)
ORPHAN_THRESHOLD = timedelta(minutes=30)
ACTIVE_STATUSES = ("running", "queued", "retrying", "stopping")

MAX_PIPELINE_RETRIES = 2

# Patterns that indicate a transient/retryable failure
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

# Step chain matching the resume endpoint logic in app/api/v1/pipelines.py
_STEP_CHAIN = {
    "pipeline_dispatch": "task_enrich_lead",
    "enrichment": "task_score_lead",
    "scoring": "task_analyze_lead",
    "analysis": "task_analyze_lead",
    "research": "task_generate_brief",
    "scout": "task_generate_brief",
    "brief_generation": "task_review_brief",
    "brief_review": "task_generate_draft",
    "draft_generation": None,
}


def _is_retryable_error(error: str | None) -> bool:
    """Check if the error string suggests a transient/retryable failure."""
    if not error:
        return True  # No error info — assume transient (e.g. stale/orphaned)
    error_lower = error.lower()
    return any(pattern in error_lower for pattern in _RETRYABLE_PATTERNS)


def _auto_resume_pipeline(pipeline_run: PipelineRun) -> bool:
    """Attempt to auto-resume a failed pipeline run if retryable.

    Returns True if the pipeline was re-queued, False if left as permanently failed.
    """
    if pipeline_run.retry_count >= MAX_PIPELINE_RETRIES:
        return False

    if not _is_retryable_error(pipeline_run.error):
        return False

    step = pipeline_run.current_step or "pipeline_dispatch"
    next_task_name = _STEP_CHAIN.get(step)
    if next_task_name is None:
        return False  # Terminal step, nothing to resume

    # Dispatch the next task
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
    """Find PipelineRun records stuck in 'running' with no activity for 30+ minutes."""
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


def sweep_zombie_leads(db) -> dict:
    """Find leads stuck in intermediate statuses and emit warnings/notifications."""
    from app.models.lead import Lead, LeadStatus
    from app.models.outreach import DraftStatus, OutreachDraft
    from app.services.notifications.notification_emitter import on_repeated_failures

    now = datetime.now(UTC)
    enriched_count = 0
    scored_count = 0
    draft_count = 0

    # Leads stuck in 'enriched' for > 1 hour
    enriched_cutoff = now - timedelta(hours=1)
    stuck_enriched = (
        db.execute(
            select(Lead).where(
                Lead.status == LeadStatus.ENRICHED,
                Lead.updated_at < enriched_cutoff,
            )
        )
        .scalars()
        .all()
    )
    for lead in stuck_enriched:
        enriched_count += 1
        logger.warning(
            "zombie_lead_enriched_stale",
            lead_id=str(lead.id),
            business_name=lead.business_name,
            updated_at=str(lead.updated_at),
        )

    # Leads stuck in 'scored' for > 24 hours and NOT qualified
    scored_cutoff = now - timedelta(hours=24)
    stuck_scored = (
        db.execute(
            select(Lead).where(
                Lead.status == LeadStatus.SCORED,
                Lead.updated_at < scored_cutoff,
            )
        )
        .scalars()
        .all()
    )
    scored_count = len(stuck_scored)
    if scored_count:
        on_repeated_failures(
            db,
            failure_type="zombie_scored_leads",
            count=scored_count,
            detail=(
                f"{scored_count} leads stuck in 'scored' for >24h without advancing to qualified."
            ),
        )

    # Leads in 'draft_ready' with drafts in PENDING_REVIEW for > 48 hours
    draft_cutoff = now - timedelta(hours=48)
    stuck_drafts = (
        db.execute(
            select(Lead)
            .join(OutreachDraft, OutreachDraft.lead_id == Lead.id)
            .where(
                Lead.status == LeadStatus.DRAFT_READY,
                OutreachDraft.status == DraftStatus.PENDING_REVIEW,
                OutreachDraft.generated_at < draft_cutoff,
            )
        )
        .scalars()
        .all()
    )
    draft_count = len(stuck_drafts)
    if draft_count:
        on_repeated_failures(
            db,
            failure_type="zombie_draft_leads",
            count=draft_count,
            detail=f"{draft_count} leads in 'draft_ready' with drafts pending review for >48h.",
        )

    result = {
        "enriched_stale": enriched_count,
        "scored_stale": scored_count,
        "draft_stale": draft_count,
    }
    if any(result.values()):
        logger.info("zombie_lead_sweep_done", **result)
    return result


def sweep_stuck_research_reports(db) -> int:
    """Find LeadResearchReport records stuck in 'running' for > 10 minutes."""
    from app.models.research_report import LeadResearchReport, ResearchStatus

    cutoff = datetime.now(UTC) - timedelta(minutes=10)
    stuck = (
        db.execute(
            select(LeadResearchReport).where(
                LeadResearchReport.status == ResearchStatus.RUNNING,
                LeadResearchReport.updated_at < cutoff,
            )
        )
        .scalars()
        .all()
    )

    count = 0
    for report in stuck:
        report.status = ResearchStatus.FAILED
        report.error = "Stuck in 'running' for >10 min — marked failed by janitor"
        count += 1
        logger.warning(
            "janitor_marked_stuck_research_report",
            report_id=str(report.id),
            lead_id=str(report.lead_id),
            updated_at=str(report.updated_at),
        )
    return count


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
            # Attempt auto-resume for retryable failures
            if _auto_resume_pipeline(pipeline_run):
                resumed_count += 1

        orphan_count = sweep_orphan_pipelines(db)

        # Attempt auto-resume for orphaned pipelines too
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

        # Sweep stuck BatchReviews (generating/reviewing for >10 min)
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

        # Sweep stuck research reports (E3-4)
        research_report_count = sweep_stuck_research_reports(db)

        # Sweep zombie leads (E3-3)
        zombie_result = sweep_zombie_leads(db)

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


@celery_app.task(name="app.workers.janitor.task_sweep_stale")
def task_sweep_stale() -> dict:
    """Celery-wrapped janitor for use with celery beat."""
    return sweep_stale_tasks()
