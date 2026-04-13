"""Batch review service — orchestrates AI team meetings.

Checks evidence thresholds, collects batch metrics, runs Executor synthesis
+ Reviewer validation, and persists results with improvement proposals.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.batch_review import BatchReview, ImprovementProposal
from app.models.lead import Lead

logger = get_logger(__name__)


def list_batch_reviews(db: Session, limit: int = 10) -> list[dict]:
    """List batch reviews with proposal counts, newest first."""
    from sqlalchemy.orm import joinedload

    reviews = (
        db.query(BatchReview)
        .options(joinedload(BatchReview.proposals))
        .order_by(BatchReview.created_at.desc())
        .limit(min(limit, 50))
        .all()
    )
    return [
        {
            "id": str(r.id),
            "trigger_reason": r.trigger_reason,
            "batch_size": r.batch_size,
            "status": r.status,
            "reviewer_verdict": r.reviewer_verdict,
            "strategy_brief": r.strategy_brief,
            "proposals_count": len(r.proposals),
            "proposals_pending": sum(1 for p in r.proposals if p.status == "pending"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reviews
    ]


def get_batch_review_detail(db: Session, review_id: uuid.UUID) -> dict | None:
    """Get batch review detail with proposals, or None if not found."""
    review = db.get(BatchReview, review_id)
    if not review:
        return None

    return {
        "id": str(review.id),
        "trigger_reason": review.trigger_reason,
        "batch_size": review.batch_size,
        "period_start": review.period_start.isoformat() if review.period_start else None,
        "period_end": review.period_end.isoformat() if review.period_end else None,
        "status": review.status,
        "executor_draft": review.executor_draft,
        "reviewer_verdict": review.reviewer_verdict,
        "reviewer_notes": review.reviewer_notes,
        "strategy_brief": review.strategy_brief,
        "metrics_json": review.metrics_json,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "proposals": [
            {
                "id": str(p.id),
                "category": p.category,
                "description": p.description,
                "impact": p.impact,
                "confidence": p.confidence,
                "evidence_summary": p.evidence_summary,
                "status": p.status,
                "approved_by": p.approved_by,
                "applied_at": p.applied_at.isoformat() if p.applied_at else None,
            }
            for p in review.proposals
        ],
    }


def check_review_threshold(db: Session) -> str | None:
    """Check if evidence thresholds are met for a batch review.

    Returns trigger reason string or None.
    """
    from app.services.settings.operational_settings_service import get_cached_settings

    ops = get_cached_settings(db)
    if not getattr(ops, "batch_review_enabled", True):
        return None

    lead_threshold = getattr(ops, "batch_review_lead_threshold", 25)
    high_threshold = getattr(ops, "batch_review_high_lead_threshold", 10)
    outcome_threshold = getattr(ops, "batch_review_outcome_threshold", 5)

    # Find the last batch review timestamp
    last_review = db.execute(
        select(BatchReview.created_at)
        .where(BatchReview.status == "completed")
        .order_by(BatchReview.created_at.desc())
        .limit(1)
    ).first()
    since = last_review[0] if last_review else datetime(2020, 1, 1, tzinfo=UTC)

    # Count leads processed since last review
    from app.models.task_tracking import PipelineRun

    total_leads = (
        db.execute(
            select(func.count(PipelineRun.id)).where(
                PipelineRun.created_at >= since,
                PipelineRun.status == "succeeded",
            )
        ).scalar()
        or 0
    )

    if total_leads >= lead_threshold:
        return f"{total_leads}_leads"

    # Count HIGH leads
    high_leads = (
        db.execute(
            select(func.count(Lead.id)).where(
                Lead.updated_at >= since,
                Lead.llm_quality == "high",
            )
        ).scalar()
        or 0
    )

    if high_leads >= high_threshold:
        return f"{high_leads}_high_leads"

    # Count new outcomes
    from app.models.outcome_snapshot import OutcomeSnapshot

    new_outcomes = (
        db.execute(
            select(func.count(OutcomeSnapshot.id)).where(OutcomeSnapshot.created_at >= since)
        ).scalar()
        or 0
    )

    if new_outcomes >= outcome_threshold:
        return f"{new_outcomes}_outcomes"

    return None


def collect_batch_data(db: Session, since: datetime) -> dict:
    """Gather metrics from the batch period for synthesis."""
    now = datetime.now(UTC)

    # Lead quality distribution
    quality_counts = dict(
        db.execute(
            select(Lead.llm_quality, func.count())
            .where(Lead.updated_at >= since)
            .group_by(Lead.llm_quality)
        ).all()
    )

    # Correction patterns
    from app.models.review_correction import ReviewCorrection

    correction_rows = db.execute(
        select(ReviewCorrection.category, func.count().label("cnt"))
        .where(ReviewCorrection.created_at >= since)
        .group_by(ReviewCorrection.category)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    corrections = {cat: cnt for cat, cnt in correction_rows}

    # Signal frequencies
    from app.models.lead_signal import LeadSignal

    signal_rows = db.execute(
        select(LeadSignal.signal_type, func.count().label("cnt"))
        .where(LeadSignal.detected_at >= since)
        .group_by(LeadSignal.signal_type)
        .order_by(func.count().desc())
        .limit(15)
    ).all()
    signals = {sig: cnt for sig, cnt in signal_rows}

    # Outcome summary
    from app.models.outcome_snapshot import OutcomeSnapshot

    outcomes = (
        db.execute(select(OutcomeSnapshot).where(OutcomeSnapshot.created_at >= since))
        .scalars()
        .all()
    )
    won = sum(1 for o in outcomes if o.outcome == "won")
    lost = len(outcomes) - won

    # LLM invocation stats
    from app.models.llm_invocation import LLMInvocation

    invocation_count = (
        db.execute(
            select(func.count(LLMInvocation.id)).where(LLMInvocation.created_at >= since)
        ).scalar()
        or 0
    )
    fallback_count = (
        db.execute(
            select(func.count(LLMInvocation.id)).where(
                LLMInvocation.created_at >= since,
                LLMInvocation.fallback_used.is_(True),
            )
        ).scalar()
        or 0
    )

    return {
        "period_start": since.isoformat(),
        "period_end": now.isoformat(),
        "leads_processed": sum(quality_counts.values()),
        "quality_distribution": quality_counts,
        "corrections": corrections,
        "signals": signals,
        "outcomes": {"won": won, "lost": lost, "total": len(outcomes)},
        "invocations": invocation_count,
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / max(invocation_count, 1), 3),
    }


def generate_batch_review(db: Session, trigger_reason: str = "manual") -> BatchReview:
    """Run the full batch review: collect data → Executor synthesis → Reviewer validation."""
    # Find period start
    last_review = db.execute(
        select(BatchReview.created_at)
        .where(BatchReview.status == "completed")
        .order_by(BatchReview.created_at.desc())
        .limit(1)
    ).first()
    since = last_review[0] if last_review else datetime(2020, 1, 1, tzinfo=UTC)

    # Collect batch data
    metrics = collect_batch_data(db, since)

    # Create review record
    review = BatchReview(
        trigger_reason=trigger_reason,
        batch_size=metrics["leads_processed"],
        period_start=since,
        period_end=datetime.now(UTC),
        metrics_json=metrics,
        status="generating",
    )
    db.add(review)
    db.flush()

    metrics_text = json.dumps(metrics, indent=2, default=str)

    # Step 1: Executor synthesis
    try:
        from app.llm.invocations.batch_review import generate_batch_synthesis_structured

        synthesis_result = generate_batch_synthesis_structured(
            batch_size=metrics["leads_processed"],
            period_start=metrics["period_start"],
            period_end=metrics["period_end"],
            trigger_reason=trigger_reason,
            metrics_json=metrics_text,
            target_type="batch_review",
            target_id=str(review.id),
        )

        if synthesis_result.parsed:
            review.executor_draft = synthesis_result.parsed.strategy_brief
        else:
            review.executor_draft = synthesis_result.raw_text or "Synthesis failed"
            review.status = "failed"
            db.flush()
            return review

    except Exception as exc:
        logger.error("batch_review_executor_failed", error=str(exc))
        review.status = "failed"
        review.executor_draft = f"Executor error: {str(exc)[:500]}"
        db.flush()
        return review

    # Step 2: Reviewer validation
    review.status = "reviewing"
    db.flush()

    try:
        from app.llm.invocations.batch_review import validate_batch_review_structured

        executor_output = json.dumps(synthesis_result.parsed.model_dump(), default=str)
        validation_result = validate_batch_review_structured(
            executor_draft=executor_output,
            metrics_json=metrics_text,
            target_type="batch_review",
            target_id=str(review.id),
        )

        if validation_result.parsed:
            review.strategy_brief = validation_result.parsed.validated_brief
            review.reviewer_verdict = "validated"
            review.reviewer_notes = validation_result.parsed.reviewer_notes

            # Persist proposals from reviewer-adjusted output
            for p in validation_result.parsed.adjusted_proposals:
                proposal = ImprovementProposal(
                    batch_review_id=review.id,
                    category=p.category,
                    description=p.description,
                    impact=p.impact,
                    confidence=p.confidence,
                    evidence_summary=p.evidence,
                )
                db.add(proposal)
        else:
            # Fallback: use Executor's proposals directly
            review.strategy_brief = review.executor_draft
            review.reviewer_verdict = "fallback"
            if synthesis_result.parsed:
                for p in synthesis_result.parsed.proposals:
                    proposal = ImprovementProposal(
                        batch_review_id=review.id,
                        category=p.category,
                        description=p.description,
                        impact=p.impact,
                        confidence=p.confidence,
                        evidence_summary=p.evidence,
                    )
                    db.add(proposal)

    except Exception as exc:
        logger.error("batch_review_reviewer_failed", error=str(exc))
        review.strategy_brief = review.executor_draft
        review.reviewer_verdict = "error"
        review.reviewer_notes = f"Reviewer error: {str(exc)[:500]}"
        # Still use Executor proposals as fallback
        if synthesis_result.parsed:
            for p in synthesis_result.parsed.proposals:
                proposal = ImprovementProposal(
                    batch_review_id=review.id,
                    category=p.category,
                    description=p.description,
                    impact=p.impact,
                    confidence=p.confidence,
                    evidence_summary=p.evidence,
                )
                db.add(proposal)

    review.status = "completed"
    db.flush()
    logger.info(
        "batch_review_completed",
        review_id=str(review.id),
        trigger=trigger_reason,
        batch_size=review.batch_size,
        proposals_count=len(review.proposals),
    )
    return review


def approve_proposal(
    db: Session, proposal_id: uuid.UUID, approved_by: str = "operator"
) -> ImprovementProposal | None:
    proposal = db.get(ImprovementProposal, proposal_id)
    if not proposal or proposal.status != "pending":
        return None
    proposal.status = "approved"
    proposal.approved_by = approved_by
    db.flush()
    return proposal


def reject_proposal(db: Session, proposal_id: uuid.UUID) -> ImprovementProposal | None:
    proposal = db.get(ImprovementProposal, proposal_id)
    if not proposal or proposal.status != "pending":
        return None
    proposal.status = "rejected"
    db.flush()
    return proposal


def apply_proposal(
    db: Session, proposal_id: uuid.UUID, result_notes: str = ""
) -> ImprovementProposal | None:
    """Mark an approved proposal as applied."""
    proposal = db.get(ImprovementProposal, proposal_id)
    if not proposal or proposal.status != "approved":
        return None
    proposal.status = "applied"
    proposal.applied_at = datetime.now(UTC)
    proposal.result_notes = (
        result_notes or f"Applied by operator at {datetime.now(UTC).isoformat()}"
    )
    db.flush()
    logger.info(
        "proposal_applied",
        proposal_id=str(proposal_id),
        category=proposal.category,
    )
    return proposal


def get_latest_strategy_brief(db: Session) -> str | None:
    review = db.execute(
        select(BatchReview)
        .where(BatchReview.status == "completed")
        .order_by(BatchReview.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return review.strategy_brief if review else None
