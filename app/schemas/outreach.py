import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OutreachDraftResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    lead_id: uuid.UUID
    subject: str
    body: str
    status: str
    generated_at: datetime
    reviewed_at: datetime | None
    sent_at: datetime | None


class OutreachDraftReview(BaseModel):
    approved: bool
    feedback: str | None = Field(None, max_length=2000)


class OutreachLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    lead_id: uuid.UUID
    draft_id: uuid.UUID | None
    action: str
    actor: str
    detail: str | None
    created_at: datetime
