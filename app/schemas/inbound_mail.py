import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.inbound_mail import InboundMailSyncStatus
from app.schemas.reply_assistant import ReplyAssistantDraftResponse


class InboundMessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    thread_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    draft_id: uuid.UUID | None
    delivery_id: uuid.UUID | None
    provider: str
    provider_mailbox: str
    provider_message_id: str | None
    message_id: str | None
    in_reply_to: str | None
    references_raw: str | None
    from_email: str | None
    from_name: str | None
    to_email: str | None
    subject: str | None
    body_text: str | None
    body_snippet: str | None
    received_at: datetime | None
    raw_metadata_json: dict | None
    classification_status: str
    classification_label: str | None
    summary: str | None
    confidence: float | None
    next_action_suggestion: str | None
    should_escalate_reviewer: bool
    classification_error: str | None
    classification_role: str | None
    classification_model: str | None
    classified_at: datetime | None
    reply_assistant_draft: ReplyAssistantDraftResponse | None = None
    created_at: datetime
    updated_at: datetime


class EmailThreadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    lead_id: uuid.UUID | None
    draft_id: uuid.UUID | None
    delivery_id: uuid.UUID | None
    provider: str
    provider_mailbox: str
    external_thread_id: str | None
    thread_key: str
    matched_via: str
    match_confidence: float | None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    message_count: int


class EmailThreadDetailResponse(EmailThreadResponse):
    messages: list[InboundMessageResponse]


class InboundMailSyncRunResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    provider: str
    provider_mailbox: str
    status: InboundMailSyncStatus | str
    fetched_count: int
    new_count: int
    deduplicated_count: int
    matched_count: int
    unmatched_count: int
    error: str | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InboundMailStatusResponse(BaseModel):
    enabled: bool
    provider: str
    mailbox: str
    search_criteria: str
    sync_limit: int
    auto_classify_inbound: bool
    reviewer_labels: list[str]
    last_sync: InboundMailSyncRunResponse | None
