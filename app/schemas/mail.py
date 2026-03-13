import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.outreach_delivery import OutreachDeliveryStatus


class OutreachDeliveryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    lead_id: uuid.UUID
    draft_id: uuid.UUID
    provider: str
    provider_message_id: str | None
    recipient_email: str
    subject_snapshot: str
    status: OutreachDeliveryStatus
    error: str | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
