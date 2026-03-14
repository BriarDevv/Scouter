import uuid
from datetime import datetime

from pydantic import BaseModel

from app.llm.roles import LLMRole
from app.models.reply_assistant import ReplyAssistantDraftStatus, ReplyAssistantReviewStatus
from app.schemas.reply_send import ReplyAssistantSendResponse


class ReplyAssistantDraftReviewResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    reply_assistant_draft_id: uuid.UUID
    inbound_message_id: uuid.UUID
    thread_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    status: ReplyAssistantReviewStatus | str
    summary: str | None
    feedback: str | None
    suggested_edits: list[str] | None
    recommended_action: str | None
    should_use_as_is: bool
    should_edit: bool
    should_escalate: bool
    reviewer_role: str | None
    reviewer_model: str | None
    task_id: str | None
    error: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReplyAssistantDraftResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    inbound_message_id: uuid.UUID
    thread_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    related_delivery_id: uuid.UUID | None
    related_outbound_draft_id: uuid.UUID | None
    status: ReplyAssistantDraftStatus | str
    subject: str
    body: str
    summary: str | None
    suggested_tone: str | None
    should_escalate_reviewer: bool
    generator_role: LLMRole | str
    generator_model: str
    edited_at: datetime | None
    edited_by: str | None
    review_is_stale: bool = False
    send_blocked_reason: str | None = None
    latest_send: ReplyAssistantSendResponse | None = None
    review: ReplyAssistantDraftReviewResponse | None = None
    created_at: datetime
    updated_at: datetime
