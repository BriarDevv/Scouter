"""Outcome tracking service — captures pipeline state when leads reach WON/LOST.

When a lead transitions to a terminal outcome, this service freezes a snapshot
of all pipeline decisions (quality, signals, brief predictions, context).
This enables Phase 4 outcome-based learning without complex historical queries.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.outcome_snapshot import OutcomeSnapshot
from app.models.review_correction import ReviewCorrection
from app.models.task_tracking import PipelineRun

logger = structlog.get_logger(__name__)


def capture_outcome_snapshot(
    db: Session,
    lead_id: uuid.UUID,
    outcome: str,
) -> OutcomeSnapshot | None:
    """Create an OutcomeSnapshot when a lead reaches WON or LOST.

    Captures the lead's score, quality, signals, full pipeline context,
    and correction count at the time of the outcome.

    Idempotent — skips if snapshot already exists for this lead.
    """
    if outcome not in ("won", "lost"):
        logger.warning("invalid_outcome", lead_id=str(lead_id), outcome=outcome)
        return None

    # Idempotency: one snapshot per lead
    existing = db.query(OutcomeSnapshot).filter_by(lead_id=lead_id).first()
    if existing:
        logger.debug("outcome_snapshot_exists", lead_id=str(lead_id), outcome=existing.outcome)
        return existing

    lead = db.get(Lead, lead_id)
    if not lead:
        logger.warning("lead_not_found_for_outcome", lead_id=str(lead_id))
        return None

    # Get latest pipeline run for context
    latest_run = (
        db.query(PipelineRun)
        .filter_by(lead_id=lead_id)
        .order_by(PipelineRun.created_at.desc())
        .first()
    )

    # Count corrections for this lead
    corrections_count = db.query(ReviewCorrection).filter_by(lead_id=lead_id).count()

    # Determine draft channel from outreach
    draft_channel = None
    try:
        from app.models.outreach import OutreachDraft
        latest_draft = (
            db.query(OutreachDraft)
            .filter_by(lead_id=lead_id)
            .order_by(OutreachDraft.created_at.desc())
            .first()
        )
        if latest_draft:
            draft_channel = latest_draft.channel if hasattr(latest_draft, "channel") else "email"
    except Exception:
        logger.debug("outcome_draft_lookup_failed", exc_info=True)

    snapshot = OutcomeSnapshot(
        lead_id=lead_id,
        outcome=outcome,
        lead_score=lead.score,
        lead_quality=lead.llm_quality,
        industry=lead.industry,
        city=lead.city,
        signals_json=[s.signal_type for s in lead.signals] if lead.signals else [],
        pipeline_context_json=latest_run.step_context_json if latest_run else None,
        draft_channel=draft_channel,
        corrections_count=corrections_count,
    )
    db.add(snapshot)
    db.commit()

    logger.info(
        "outcome_snapshot_captured",
        lead_id=str(lead_id),
        outcome=outcome,
        score=lead.score,
        quality=lead.llm_quality,
        industry=lead.industry,
        corrections=corrections_count,
    )
    return snapshot
