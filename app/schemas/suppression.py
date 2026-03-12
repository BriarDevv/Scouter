import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SuppressionCreate(BaseModel):
    email: str | None = Field(None, max_length=320)
    domain: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    reason: str | None = Field(None, max_length=2000)


class SuppressionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str | None
    domain: str | None
    phone: str | None
    reason: str | None
    added_at: datetime
