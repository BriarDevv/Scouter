"""Batch review API — list, detail, generate, approve/reject proposals."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.batch_review import (
    BatchReviewDetailResponse,
    BatchReviewSummaryItem,
    ProposalActionResponse,
    TriggerBatchReviewResponse,
)
from app.services.pipeline.batch_review_service import (
    apply_proposal as _apply,
)
from app.services.pipeline.batch_review_service import (
    approve_proposal as _approve,
)
from app.services.pipeline.batch_review_service import (
    get_batch_review_detail,
)
from app.services.pipeline.batch_review_service import (
    list_batch_reviews as _list_batch_reviews,
)
from app.services.pipeline.batch_review_service import (
    reject_proposal as _reject,
)

router = APIRouter(prefix="/batch-reviews", tags=["batch-reviews"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[BatchReviewSummaryItem])
def list_batch_reviews(db: DbSession, limit: int = 10):
    """List batch reviews, newest first."""
    return _list_batch_reviews(db, limit=limit)


@router.get("/{review_id}", response_model=BatchReviewDetailResponse)
def get_batch_review(review_id: uuid.UUID, db: DbSession):
    """Get batch review detail with proposals."""
    result = get_batch_review_detail(db, review_id)
    if not result:
        raise HTTPException(status_code=404, detail="Batch review not found")
    return result


@router.post("/generate", response_model=TriggerBatchReviewResponse)
def trigger_batch_review(db: DbSession):
    """Manually trigger a batch review."""
    from app.workers.batch_review_tasks import task_generate_batch_review_manual

    result = task_generate_batch_review_manual.delay()
    return {
        "ok": True,
        "task_id": str(result.id),
        "message": "Batch review generation started.",
    }


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalActionResponse)
def approve_proposal(proposal_id: uuid.UUID, db: DbSession):
    """Approve an improvement proposal."""
    proposal = _approve(db, proposal_id, approved_by="operator")
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    db.commit()
    return {
        "id": str(proposal.id),
        "status": proposal.status,
        "approved_by": proposal.approved_by,
    }


@router.post("/proposals/{proposal_id}/apply", response_model=ProposalActionResponse)
def apply_proposal_endpoint(proposal_id: uuid.UUID, db: DbSession):
    """Mark an approved proposal as applied."""
    proposal = _apply(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not approved")
    db.commit()
    return {
        "id": str(proposal.id),
        "status": proposal.status,
        "applied_at": proposal.applied_at.isoformat() if proposal.applied_at else None,
    }


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalActionResponse)
def reject_proposal(proposal_id: uuid.UUID, db: DbSession):
    """Reject an improvement proposal."""
    proposal = _reject(db, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found or not pending")
    db.commit()
    return {
        "id": str(proposal.id),
        "status": proposal.status,
    }
