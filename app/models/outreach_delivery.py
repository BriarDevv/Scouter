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
    from app.models.outreach import OutreachDraft
    from app.models.reply_assistant import ReplyAssistantDraft


class OutreachDeliveryStatus(enum.StrEnum):
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class OutreachDelivery(Base):
    __tablename__ = "outreach_deliveries"
    __table_args__ = (
        Index("ix_outreach_deliveries_draft_id", "draft_id"),
        Index("ix_outreach_deliveries_lead_id", "lead_id"),
        Index("ix_outreach_deliveries_status", "status"),
        Index("ix_outreach_deliveries_provider_message_id", "provider_message_id"),
        Index(
            "uq_outreach_deliveries_active_or_sent_per_draft",
            "draft_id",
            unique=True,
            postgresql_where=text("status IN ('sending', 'sent')"),
            sqlite_where=text("status IN ('sending', 'sent')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("outreach_drafts.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[OutreachDeliveryStatus] = mapped_column(
        Enum(
            OutreachDeliveryStatus,
            name="outreachdeliverystatus",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=OutreachDeliveryStatus.SENDING,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped[Lead] = relationship("Lead", back_populates="outreach_deliveries")  # noqa: F821
    draft: Mapped[OutreachDraft] = relationship(  # noqa: F821
        "OutreachDraft", back_populates="deliveries"
    )
    email_threads: Mapped[list[EmailThread]] = relationship(  # noqa: F821
        "EmailThread", back_populates="delivery"
    )
    inbound_messages: Mapped[list[InboundMessage]] = relationship(  # noqa: F821
        "InboundMessage", back_populates="delivery"
    )
    reply_assistant_drafts: Mapped[list[ReplyAssistantDraft]] = relationship(  # noqa: F821
        "ReplyAssistantDraft", back_populates="related_delivery"
    )
