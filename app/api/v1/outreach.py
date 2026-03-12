import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models.outreach import DraftStatus
from app.schemas.outreach import OutreachDraftResponse, OutreachDraftReview
from app.services.outreach_service import generate_outreach_draft, list_drafts, review_draft
from app.workers.tasks import task_generate_draft

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/{lead_id}/draft", response_model=OutreachDraftResponse, status_code=201)
def generate_draft(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Generate an outreach email draft for a lead (sync)."""
    draft = generate_outreach_draft(db, lead_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Lead not found or suppressed")
    return draft


@router.post("/{lead_id}/draft/async")
def generate_draft_async(lead_id: uuid.UUID):
    """Queue outreach draft generation as an async task."""
    task = task_generate_draft.delay(str(lead_id))
    return {"task_id": task.id, "status": "queued"}


@router.get("/drafts", response_model=list[OutreachDraftResponse])
def list_all_drafts(
    status: DraftStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
):
    """List outreach drafts, optionally filtered by status."""
    return list_drafts(db, status=status, page=page, page_size=page_size)


@router.post("/drafts/{draft_id}/review", response_model=OutreachDraftResponse)
def review(draft_id: uuid.UUID, data: OutreachDraftReview, db: Session = Depends(get_session)):
    """Human-in-the-loop: approve or reject an outreach draft."""
    draft = review_draft(db, draft_id, approved=data.approved, feedback=data.feedback)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft
