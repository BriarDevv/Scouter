from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.inbound_mail import EmailThread, InboundMessage
    from app.models.lead import Lead
    from app.models.reply_assistant import ReplyAssistantDraft


class ReplyAssistantSendStatus(enum.StrEnum):
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class ReplyAssistantSend(Base):
    __tablename__ = "reply_assistant_sends"
    __table_args__ = (
        Index("ix_reply_assistant_sends_draft_id", "reply_assistant_draft_id"),
        Index("ix_reply_assistant_sends_inbound_message_id", "inbound_message_id"),
        Index("ix_reply_assistant_sends_thread_id", "thread_id"),
        Index("ix_reply_assistant_sends_lead_id", "lead_id"),
        Index("ix_reply_assistant_sends_status", "status"),
        Index("ix_reply_assistant_sends_provider_message_id", "provider_message_id"),
        Index("ix_reply_assistant_sends_created_at", "created_at"),
        Index(
            "uq_reply_assistant_sends_active_or_sent_per_draft",
            "reply_assistant_draft_id",
            unique=True,
            postgresql_where=text("status IN ('sending', 'sent')"),
            sqlite_where=text("status IN ('sending', 'sent')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reply_assistant_draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("reply_assistant_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    inbound_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("inbound_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("email_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ReplyAssistantSendStatus] = mapped_column(
        Enum(
            ReplyAssistantSendStatus,
            name="replyassistantsendstatus",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ReplyAssistantSendStatus.SENDING,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    from_email_snapshot: Mapped[str | None] = mapped_column(String(320), nullable=True)
    reply_to_snapshot: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    body_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    in_reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    references_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    draft: Mapped[ReplyAssistantDraft] = relationship(  # noqa: F821
        "ReplyAssistantDraft",
        back_populates="sends",
    )
    inbound_message: Mapped[InboundMessage] = relationship(  # noqa: F821
        "InboundMessage",
        back_populates="reply_assistant_sends",
    )
    thread: Mapped[EmailThread | None] = relationship(  # noqa: F821
        "EmailThread",
        back_populates="reply_assistant_sends",
    )
    lead: Mapped[Lead | None] = relationship("Lead", back_populates="reply_assistant_sends")  # noqa: F821
