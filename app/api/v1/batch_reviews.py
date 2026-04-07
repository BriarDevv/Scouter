"""Batch review API — list, detail, generate, approve/reject proposals."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(prefix="/batch-reviews", tags=["batch-reviews"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("")
def list_batch_reviews(db: DbSession, limit: int = 10):
    """List batch reviews, newest first."""
    from app.models.batch_review import BatchReview

    reviews = (
        db.query(BatchReview)
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


@router.get("/{review_id}")
def get_batch_review(review_id: uuid.UUID, db: DbSession):
    """Get batch review detail with proposals."""
    from app.models.batch_review import BatchReview

    review = db.get(BatchReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Batch review not found")

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


@router.post("/generate")
def trigger_batch_review(db: DbSession):
    """Manually trigger a batch review."""
    from app.workers.batch_review_tasks import task_generate_batch_review_manual

    result = task_generate_batch_review_manual.delay()
    return {
        "ok": True,
        "task_id": str(result.id),
        "message": "Batch review generation started.",
    }


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: uuid.UUID, db: DbSession):
    """Approve an improvement proposal."""
    from app.services.pipeline.batch_review_service import approve_proposal as _approve

    proposal = _approve(db, proposal_id, approved_by="operator")
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    db.commit()
    return {
        "id": str(proposal.id),
        "status": proposal.status,
        "approved_by": proposal.approved_by,
    }


@router.post("/proposals/{proposal_id}/apply")
def apply_proposal_endpoint(proposal_id: uuid.UUID, db: DbSession):
    """Mark an approved proposal as applied."""
    from app.services.pipeline.batch_review_service import apply_proposal as _apply

    proposal = _apply(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not approved")
    db.commit()
    return {
        "id": str(proposal.id),
        "status": proposal.status,
        "applied_at": proposal.applied_at.isoformat() if proposal.applied_at else None,
    }


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: uuid.UUID, db: DbSession):
    """Reject an improvement proposal."""
    from app.services.pipeline.batch_review_service import reject_proposal as _reject

    proposal = _reject(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    db.commit()
    return {
        "id": str(proposal.id),
        "status": proposal.status,
    }
