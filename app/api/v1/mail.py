import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.mail.inbound_provider import InboundMailProviderError
from app.schemas.inbound_mail import (
    EmailThreadDetailResponse,
    EmailThreadResponse,
    InboundMailStatusResponse,
    InboundMailSyncRunResponse,
    InboundMessageResponse,
)
from app.services.inbound_mail_service import (
    InboundMailDisabledError,
    get_email_thread,
    get_inbound_message,
    get_inbound_sync_status,
    list_email_threads,
    list_inbound_messages,
    sync_inbound_messages,
)
from app.services.reply_classification_service import (
    classify_inbound_message,
    classify_pending_inbound_messages,
)
from app.core.config import settings

router = APIRouter(prefix="/mail/inbound", tags=["mail-inbound"])


@router.post("/sync", response_model=InboundMailSyncRunResponse)
def sync_inbound_mail(
    limit: int | None = Query(None, ge=1, le=200),
    db: Session = Depends(get_session),
):
    try:
        return sync_inbound_messages(db, limit=limit)
    except InboundMailDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except InboundMailProviderError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/messages", response_model=list[InboundMessageResponse])
def list_messages(
    lead_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
    classification_status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
):
    return list_inbound_messages(
        db,
        lead_id=lead_id,
        thread_id=thread_id,
        classification_status=classification_status,
        limit=limit,
    )


@router.post("/messages/classify-pending", response_model=list[InboundMessageResponse])
def classify_pending_messages(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_session),
):
    return classify_pending_inbound_messages(db, limit=limit)


@router.get("/messages/{message_id}", response_model=InboundMessageResponse)
def get_message(message_id: uuid.UUID, db: Session = Depends(get_session)):
    message = get_inbound_message(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbound message not found")
    return message


@router.get("/threads", response_model=list[EmailThreadResponse])
def list_threads(
    lead_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
):
    return list_email_threads(db, lead_id=lead_id, limit=limit)


@router.get("/threads/{thread_id}", response_model=EmailThreadDetailResponse)
def get_thread(thread_id: uuid.UUID, db: Session = Depends(get_session)):
    thread = get_email_thread(db, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Email thread not found")
    return thread


@router.get("/status", response_model=InboundMailStatusResponse)
def get_status(db: Session = Depends(get_session)):
    return {
        "enabled": settings.MAIL_INBOUND_ENABLED,
        "provider": settings.MAIL_INBOUND_PROVIDER.lower(),
        "mailbox": settings.MAIL_IMAP_MAILBOX,
        "search_criteria": settings.MAIL_IMAP_SEARCH_CRITERIA,
        "sync_limit": settings.MAIL_INBOUND_SYNC_LIMIT,
        "auto_classify_inbound": settings.MAIL_AUTO_CLASSIFY_INBOUND,
        "reviewer_labels": list(settings.mail_use_reviewer_for_labels),
        "last_sync": get_inbound_sync_status(db),
    }


@router.post("/messages/{message_id}/classify", response_model=InboundMessageResponse)
def classify_message(message_id: uuid.UUID, db: Session = Depends(get_session)):
    message = classify_inbound_message(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbound message not found")
    return message
