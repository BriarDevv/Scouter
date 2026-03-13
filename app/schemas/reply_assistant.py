import uuid
from datetime import datetime

from pydantic import BaseModel

from app.llm.roles import LLMRole
from app.models.reply_assistant import ReplyAssistantDraftStatus


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
    created_at: datetime
    updated_at: datetime
