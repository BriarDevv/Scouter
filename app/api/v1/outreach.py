import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.request_context import get_correlation_id
from app.db.session import get_db
from app.mail.provider import MailProviderError
from app.models.outreach import DraftStatus
from app.schemas.mail import OutreachDeliveryResponse
from app.schemas.outreach import (
    OutreachDraftResponse,
    OutreachDraftReview,
    OutreachDraftUpdate,
    OutreachLogResponse,
)
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.outreach.mail_service import (
    DraftAlreadySentError,
    DraftNotApprovedError,
    DraftRecipientMissingError,
    DraftSendRateLimitError,
    MailDisabledError,
    list_deliveries,
    send_draft,
)
from app.services.outreach.outreach_service import (
    generate_outreach_draft,
    generate_whatsapp_draft,
    get_draft,
    list_drafts,
    list_logs,
    review_draft,
    update_draft,
)
from app.services.pipeline.task_tracking_service import queue_task_run
from app.workers.tasks import task_generate_draft

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/{lead_id}/draft", response_model=OutreachDraftResponse, status_code=201)
def generate_draft(
    lead_id: uuid.UUID,
    channel: str = Query("email", pattern="^(email|whatsapp)$"),
    db: Session = Depends(get_db),
):
    """Generate an outreach draft for a lead (sync)."""
    if channel == "whatsapp":
        draft = generate_whatsapp_draft(db, lead_id)
    else:
        draft = generate_outreach_draft(db, lead_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Lead not found or suppressed")
    return draft


@router.post("/{lead_id}/draft/async", response_model=TaskEnqueueResponse)
def generate_draft_async(
    lead_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Queue outreach draft generation as an async task."""
    correlation_id = get_correlation_id(request)
    task = task_generate_draft.delay(str(lead_id), correlation_id=correlation_id)
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_generate_draft",
        queue="llm",
        lead_id=lead_id,
        correlation_id=correlation_id,
        current_step="draft_generation",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "llm",
        "lead_id": lead_id,
        "current_step": "draft_generation",
    }


@router.get("/drafts", response_model=list[OutreachDraftResponse])
def list_all_drafts(
    status: DraftStatus | None = None,
    lead_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List outreach drafts, optionally filtered by status."""
    return list_drafts(db, status=status, lead_id=lead_id, page=page, page_size=page_size)


@router.get("/drafts/{draft_id}", response_model=OutreachDraftResponse)
def get_draft_by_id(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a single outreach draft by ID."""
    draft = get_draft(db, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("/drafts/{draft_id}/send", response_model=OutreachDeliveryResponse)
def send_draft_by_id(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    """Send an approved outreach draft through the configured mail provider."""
    try:
        delivery = send_draft(db, draft_id)
    except MailDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DraftSendRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except DraftNotApprovedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DraftAlreadySentError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except DraftRecipientMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except MailProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not delivery:
        raise HTTPException(status_code=404, detail="Draft not found")
    return delivery


@router.get("/drafts/{draft_id}/deliveries", response_model=list[OutreachDeliveryResponse])
def list_draft_deliveries(draft_id: uuid.UUID, db: Session = Depends(get_db)):
    """List delivery attempts for a specific outreach draft."""
    draft = get_draft(db, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return list_deliveries(db, draft_id)


@router.post("/drafts/{draft_id}/review", response_model=OutreachDraftResponse)
def review(draft_id: uuid.UUID, data: OutreachDraftReview, db: Session = Depends(get_db)):
    """Human-in-the-loop: approve or reject an outreach draft."""
    draft = review_draft(db, draft_id, approved=data.approved, feedback=data.feedback)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/drafts/{draft_id}", response_model=OutreachDraftResponse)
def patch_draft(draft_id: uuid.UUID, data: OutreachDraftUpdate, db: Session = Depends(get_db)):
    """Update outreach draft content or status."""
    draft = update_draft(
        db,
        draft_id,
        subject=data.subject,
        body=data.body,
        status=data.status,
        feedback=data.feedback,
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/logs", response_model=list[OutreachLogResponse])
def list_outreach_logs(
    lead_id: uuid.UUID | None = None,
    draft_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List recent outreach activity logs."""
    return list_logs(db, lead_id=lead_id, draft_id=draft_id, limit=limit)
