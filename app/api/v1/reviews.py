import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.inbound_mail import InboundMessage
from app.models.lead import Lead
from app.models.outreach import OutreachDraft
from app.schemas.review import DraftReviewResponse, InboundReplyReviewResponse, LeadReviewResponse
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.pipeline.task_tracking_service import queue_task_run
from app.services.reviews.review_service import (
    get_corrections_summary,
    review_draft_with_reviewer,
    review_inbound_message_with_reviewer,
    review_lead_with_reviewer,
)
from app.workers.review_tasks import (
    task_review_draft,
    task_review_inbound_message,
    task_review_lead,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/leads/{lead_id}", response_model=LeadReviewResponse)
def review_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Run a reviewer-only second opinion for a lead."""
    payload = review_lead_with_reviewer(db, lead_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.commit()
    return payload


@router.post("/leads/{lead_id}/async", response_model=TaskEnqueueResponse)
def review_lead_async(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Queue a reviewer-only second opinion for a lead."""
    if not db.get(Lead, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")

    task = task_review_lead.delay(str(lead_id))
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_review_lead",
        queue="reviewer",
        lead_id=lead_id,
        current_step="lead_review",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "reviewer",
        "lead_id": lead_id,
        "current_step": "lead_review",
    }


@router.post("/drafts/{draft_id}", response_model=DraftReviewResponse)
def review_draft(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    """Run a reviewer-only second opinion for an outreach draft."""
    payload = review_draft_with_reviewer(db, draft_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Draft not found")
    db.commit()
    return payload


@router.post("/drafts/{draft_id}/async", response_model=TaskEnqueueResponse)
def review_draft_async(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    """Queue a reviewer-only second opinion for an outreach draft."""
    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    task = task_review_draft.delay(str(draft_id))
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_review_draft",
        queue="reviewer",
        lead_id=draft.lead_id,
        current_step="draft_review",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "reviewer",
        "lead_id": draft.lead_id,
        "current_step": "draft_review",
    }


@router.post("/inbound/messages/{message_id}", response_model=InboundReplyReviewResponse)
def review_inbound_message(message_id: uuid.UUID, db: Session = Depends(get_db)):
    """Run a reviewer-only second opinion for an inbound reply."""
    payload = review_inbound_message_with_reviewer(db, message_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Inbound message not found")
    db.commit()
    return payload


@router.post("/inbound/messages/{message_id}/async", response_model=TaskEnqueueResponse)
def review_inbound_message_async(message_id: uuid.UUID, db: Session = Depends(get_db)):
    """Queue a reviewer-only second opinion for an inbound reply."""
    message = db.get(InboundMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbound message not found")

    task = task_review_inbound_message.delay(str(message_id))
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_review_inbound_message",
        queue="reviewer",
        lead_id=message.lead_id,
        current_step="inbound_reply_review",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "reviewer",
        "lead_id": message.lead_id,
        "current_step": "inbound_reply_review",
    }


@router.get("/corrections/summary")
def corrections_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Aggregate reviewer corrections by category for the last N days.

    Returns top correction categories with count and recent examples.
    Used by dashboard to surface patterns for prompt improvement.
    """
    return get_corrections_summary(db, days=days)
