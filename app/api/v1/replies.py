import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.reply_assistant import (
    ReplyAssistantDraftResponse,
    ReplyAssistantDraftReviewResponse,
)
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.reply_draft_review_service import (
    ensure_reply_assistant_review_pending,
    get_reply_assistant_review_for_message,
)
from app.services.reply_response_service import (
    generate_reply_assistant_draft,
    get_inbound_message_with_reply_context,
    get_reply_assistant_draft_for_message,
)
from app.services.task_tracking_service import queue_task_run
from app.workers.tasks import task_review_reply_assistant_draft

router = APIRouter(prefix="/replies", tags=["reply-assistant"])


@router.post("/{message_id}/draft-response", response_model=ReplyAssistantDraftResponse)
def create_or_refresh_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_session)):
    message = get_inbound_message_with_reply_context(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Inbound message not found")
    return generate_reply_assistant_draft(db, message_id)


@router.get("/{message_id}/draft-response", response_model=ReplyAssistantDraftResponse)
def get_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_session)):
    draft = get_reply_assistant_draft_for_message(db, message_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Reply assistant draft not found")
    return draft


@router.post("/{message_id}/draft-response/review", response_model=TaskEnqueueResponse)
def review_reply_draft(message_id: uuid.UUID, db: Session = Depends(get_session)):
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
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "reviewer",
        "lead_id": message.lead_id,
        "current_step": "reply_draft_review",
    }


@router.get("/{message_id}/draft-response/review", response_model=ReplyAssistantDraftReviewResponse)
def get_reply_draft_review(message_id: uuid.UUID, db: Session = Depends(get_session)):
    review = get_reply_assistant_review_for_message(db, message_id)
    if not review:
        raise HTTPException(status_code=404, detail="Reply assistant draft review not found")
    return review
