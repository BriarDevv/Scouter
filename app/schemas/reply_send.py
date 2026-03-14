import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.reply_assistant_send import ReplyAssistantSendStatus


class ReplyAssistantDraftUpdateRequest(BaseModel):
    subject: str | None = Field(None, max_length=500)
    body: str | None = Field(None, max_length=65535)
    edited_by: str | None = Field(default=None, max_length=100)


class ReplyAssistantSendResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    reply_assistant_draft_id: uuid.UUID
    inbound_message_id: uuid.UUID
    thread_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    status: ReplyAssistantSendStatus | str
    provider: str
    provider_message_id: str | None
    recipient_email: str
    from_email_snapshot: str | None
    reply_to_snapshot: str | None
    subject_snapshot: str
    body_snapshot: str
    in_reply_to: str | None
    references_raw: str | None
    error: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReplyAssistantSendStatusResponse(BaseModel):
    draft_id: uuid.UUID
    inbound_message_id: uuid.UUID
    review_is_stale: bool
    send_blocked_reason: str | None
    latest_send: ReplyAssistantSendResponse | None
    sent: bool
