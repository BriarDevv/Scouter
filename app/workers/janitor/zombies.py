"""Zombie lead + stuck research sweeps.

A zombie lead is a Lead row stuck in an intermediate status longer than
its expected SLA window. The janitor detects them, logs warnings, and
(for scored/draft-ready cases) emits operator notifications. Research
reports left in RUNNING status are marked FAILED so the pipeline can
progress.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger

logger = get_logger(__name__)


def sweep_zombie_leads(db) -> dict:
    """Log warnings + emit notifications for leads stuck in intermediate status."""
    from app.models.lead import Lead, LeadStatus
    from app.models.outreach import DraftStatus, OutreachDraft
    from app.services.notifications.notification_emitter import on_repeated_failures

    now = datetime.now(UTC)
    enriched_count = 0
    scored_count = 0
    draft_count = 0

    # Leads stuck in 'enriched' for > 1 hour.
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

    # Leads stuck in 'scored' for > 24 hours and NOT qualified.
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

    # Leads in 'draft_ready' with drafts in PENDING_REVIEW for > 48 hours.
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
            detail=(f"{draft_count} leads in 'draft_ready' with drafts pending review for >48h."),
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
    """Mark LeadResearchReport rows stuck in 'running' for > 10 minutes as failed."""
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
