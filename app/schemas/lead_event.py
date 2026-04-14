"""Pydantic schemas for the LeadEvent timeline endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    old_status: str | None
    new_status: str | None
    payload_json: dict | None
    actor: str
    created_at: datetime


class LeadEventListOut(BaseModel):
    items: list[LeadEventOut]
    total: int
    limit: int
    offset: int
