"""Pydantic schemas for notifications."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    category: str
    severity: str
    title: str
    message: str
    source_kind: str | None = None
    source_id: UUID | None = None
    metadata: dict | None = None
    status: str
    read_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    channel_state: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    unread_count: int


class NotificationCountsResponse(BaseModel):
    total_unread: int
    business: int
    system: int
    security: int
    critical: int
    high: int


class NotificationStatusUpdate(BaseModel):
    status: str


class NotificationBulkAction(BaseModel):
    ids: list[UUID] | None = None
    action: str  # mark_read, mark_resolved
    category: str | None = None
