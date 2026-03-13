import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.reply_assistant import ReplyAssistantDraftResponse
from app.services.reply_response_service import (
    generate_reply_assistant_draft,
    get_inbound_message_with_reply_context,
    get_reply_assistant_draft_for_message,
)

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
