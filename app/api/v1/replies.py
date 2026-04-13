import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reply_assistant import (
    ReplyAssistantDraftResponse,
    ReplyAssistantDraftReviewResponse,
)
from app.schemas.reply_send import (
    ReplyAssistantDraftUpdateRequest,
    ReplyAssistantSendResponse,
    ReplyAssistantSendStatusResponse,
)
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.inbox.reply_draft_review_service import (
    ensure_reply_assistant_review_pending,
    get_reply_assistant_review_for_message,
)
from app.services.inbox.reply_response_service import (
    generate_reply_assistant_draft,
    get_inbound_message_with_reply_context,
    get_reply_assistant_draft_for_message,
)
from app.services.inbox.reply_send_service import (
    ReplyDraftAlreadySendingError,
    ReplyDraftAlreadySentError,
    ReplyDraftNotFoundError,
    ReplyDraftValidationError,
    get_reply_send_status,
    send_reply_assistant_draft,
    update_reply_assistant_draft,
)
from app.services.outreach.mail_service import (
    DraftRecipientMissingError,
    MailConfigurationError,
    MailDisabledError,
)
from app.services.pipeline.task_tracking_service import queue_task_run
from app.workers.review_tasks import task_review_reply_assistant_draft

router = APIRouter(prefix="/replies", tags=["reply-assistant"])


@router.post("/{message_id}/draft-response", response_model=ReplyAssistantDraftResponse)
def create_or_refresh_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_db)):
    message = get_inbound_message_with_reply_context(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbound message not found")
    return generate_reply_assistant_draft(db, message_id)


@router.get("/{message_id}/draft-response", response_model=ReplyAssistantDraftResponse)
def get_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_db)):
    draft = get_reply_assistant_draft_for_message(db, message_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Reply assistant draft not found")
    return draft


@router.patch("/{message_id}/draft-response", response_model=ReplyAssistantDraftResponse)
def patch_reply_draft(
    message_id: uuid.UUID,
    payload: ReplyAssistantDraftUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        draft = update_reply_assistant_draft(
            db,
            message_id,
            subject=payload.subject,
            body=payload.body,
            edited_by=payload.edited_by,
        )
        db.commit()
        return draft
    except ReplyDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{message_id}/draft-response/send", response_model=ReplyAssistantSendResponse)
def send_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        result = send_reply_assistant_draft(db, message_id)
        db.commit()
        return result
    except ReplyDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReplyDraftAlreadySentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ReplyDraftAlreadySendingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ReplyDraftValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DraftRecipientMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (MailDisabledError, MailConfigurationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/{message_id}/draft-response/send-status", response_model=ReplyAssistantSendStatusResponse
)
def get_reply_draft_send_status(message_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return get_reply_send_status(db, message_id)
    except ReplyDraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{message_id}/draft-response/review", response_model=TaskEnqueueResponse)
def review_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_db)):
    message = get_inbound_message_with_reply_context(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbound message not found")
    if not message.reply_assistant_draft:
        raise HTTPException(status_code=404, detail="Reply assistant draft not found")

    task = task_review_reply_assistant_draft.delay(str(message_id))
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_review_reply_assistant_draft",
        queue="reviewer",
        lead_id=message.lead_id,
        current_step="reply_draft_review",
    )
    ensure_reply_assistant_review_pending(db, message_id, task_id=task.id)
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "reviewer",
        "lead_id": message.lead_id,
        "current_step": "reply_draft_review",
    }


@router.get("/{message_id}/draft-response/review", response_model=ReplyAssistantDraftReviewResponse)
def get_reply_draft_review(message_id: uuid.UUID, db: Session = Depends(get_db)):
    review = get_reply_assistant_review_for_message(db, message_id)
    if not review:
        raise HTTPException(status_code=404, detail="Reply assistant draft review not found")
    return review
