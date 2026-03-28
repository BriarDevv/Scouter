from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4096)
    attachments: list[str] | None = None


class ConfirmationRequest(BaseModel):
    confirmed: bool


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel: str
    title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str | None
    message_count: int
    last_message_at: datetime | None
    created_at: datetime


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_name: str
    arguments: dict | None = None
    result: dict | None = None
    error: str | None = None
    status: str
    duration_ms: int | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str | None
    attachments: list[dict] | None = None
    tool_calls: list[ToolCallResponse] = []
    model: str | None = None
    created_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse] = []
