from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.outreach import OutreachDraft
    from app.models.outreach_delivery import OutreachDelivery
    from app.models.reply_assistant import ReplyAssistantDraft
    from app.models.reply_assistant_send import ReplyAssistantSend


class InboundMailClassificationStatus(enum.StrEnum):
    PENDING = "pending"
    CLASSIFYING = "classifying"
    CLASSIFIED = "classified"
    FAILED = "failed"


class InboundMailSyncStatus(enum.StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EmailThread(Base):
    __tablename__ = "email_threads"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_mailbox",
            "thread_key",
            name="uq_email_threads_provider_mailbox_thread_key",
        ),
        Index("ix_email_threads_lead_id", "lead_id"),
        Index("ix_email_threads_delivery_id", "delivery_id"),
        Index("ix_email_threads_last_message_at", "last_message_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("outreach_drafts.id", ondelete="SET NULL"), nullable=True
    )
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("outreach_deliveries.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_mailbox: Mapped[str] = mapped_column(String(255), nullable=False)
    external_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thread_key: Mapped[str] = mapped_column(String(512), nullable=False)
    matched_via: Mapped[str] = mapped_column(String(50), nullable=False, default="unmatched")
    match_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped[Lead | None] = relationship("Lead", back_populates="email_threads")  # noqa: F821
    draft: Mapped[OutreachDraft | None] = relationship(  # noqa: F821
        "OutreachDraft", back_populates="email_threads"
    )
    delivery: Mapped[OutreachDelivery | None] = relationship(  # noqa: F821
        "OutreachDelivery", back_populates="email_threads"
    )
    messages: Mapped[list[InboundMessage]] = relationship(
        "InboundMessage", back_populates="thread", order_by="InboundMessage.received_at.desc()"
    )
    reply_assistant_drafts: Mapped[list[ReplyAssistantDraft]] = relationship(  # noqa: F821
        "ReplyAssistantDraft", back_populates="thread"
    )
    reply_assistant_sends: Mapped[list[ReplyAssistantSend]] = relationship(  # noqa: F821
        "ReplyAssistantSend", back_populates="thread"
    )

    @property
    def message_count(self) -> int:
        return len(self.messages)


class InboundMessage(Base):
    __tablename__ = "inbound_messages"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_inbound_messages_dedupe_key"),
        Index("ix_inbound_messages_thread_id", "thread_id"),
        Index("ix_inbound_messages_lead_id", "lead_id"),
        Index("ix_inbound_messages_delivery_id", "delivery_id"),
        Index("ix_inbound_messages_received_at", "received_at"),
        Index("ix_inbound_messages_provider_message_id", "provider_message_id"),
        Index("ix_inbound_messages_message_id", "message_id"),
        Index("ix_inbound_messages_classification_status", "classification_status"),
        Index("ix_inbound_messages_classification_label", "classification_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dedupe_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("email_threads.id", ondelete="SET NULL"), nullable=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("outreach_drafts.id", ondelete="SET NULL"), nullable=True
    )
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("outreach_deliveries.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_mailbox: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    references_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_email: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    classification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=InboundMailClassificationStatus.PENDING.value
    )
    classification_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    next_action_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    should_escalate_reviewer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    classification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classification_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    thread: Mapped[EmailThread | None] = relationship("EmailThread", back_populates="messages")
    lead: Mapped[Lead | None] = relationship("Lead", back_populates="inbound_messages")  # noqa: F821
    draft: Mapped[OutreachDraft | None] = relationship(  # noqa: F821
        "OutreachDraft", back_populates="inbound_messages"
    )
    delivery: Mapped[OutreachDelivery | None] = relationship(  # noqa: F821
        "OutreachDelivery", back_populates="inbound_messages"
    )
    reply_assistant_draft: Mapped[ReplyAssistantDraft | None] = relationship(  # noqa: F821
        "ReplyAssistantDraft",
        back_populates="inbound_message",
        cascade="all, delete-orphan",
        uselist=False,
    )
    reply_assistant_sends: Mapped[list[ReplyAssistantSend]] = relationship(  # noqa: F821
        "ReplyAssistantSend", back_populates="inbound_message"
    )


class InboundMailSyncRun(Base):
    __tablename__ = "inbound_mail_sync_runs"
    __table_args__ = (
        Index("ix_inbound_mail_sync_runs_status", "status"),
        Index("ix_inbound_mail_sync_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_mailbox: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=InboundMailSyncStatus.RUNNING.value
    )
    fetched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduplicated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmatched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
