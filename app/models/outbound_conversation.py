"""Outbound conversation — tracks Mote's outreach conversations with clients.

Each OutboundConversation represents a thread between Mote and a client
(via WhatsApp or email). It tracks the initial outreach, any replies,
and the conversation state for operator visibility.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConversationStatus(str, enum.Enum):
    DRAFT_READY = "draft_ready"
    SENT = "sent"
    DELIVERED = "delivered"
    REPLIED = "replied"
    MEETING = "meeting"
    CLOSED = "closed"
    OPERATOR_TOOK_OVER = "operator_took_over"


class OutboundConversation(Base):
    __tablename__ = "outbound_conversations"
    __table_args__ = (
        Index("ix_outbound_conversations_lead_id", "lead_id"),
        Index("ix_outbound_conversations_status", "status"),
        Index("ix_outbound_conversations_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("outreach_drafts.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # "whatsapp" | "email"
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), nullable=False, default=ConversationStatus.DRAFT_READY
    )
    messages_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # [{role: "mote"|"client", content: "...", timestamp: "...", provider_message_id: "..."}]
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="outreach")
    # "outreach" (first msg only) | "closer" (full conversation)
    operator_took_over: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
