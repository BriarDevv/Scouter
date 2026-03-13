import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReplyAssistantDraftStatus(str, enum.Enum):
    GENERATED = "generated"


class ReplyAssistantDraft(Base):
    __tablename__ = "reply_assistant_drafts"
    __table_args__ = (
        UniqueConstraint(
            "inbound_message_id",
            name="uq_reply_assistant_drafts_inbound_message_id",
        ),
        Index("ix_reply_assistant_drafts_lead_id", "lead_id"),
        Index("ix_reply_assistant_drafts_thread_id", "thread_id"),
        Index("ix_reply_assistant_drafts_delivery_id", "related_delivery_id"),
        Index("ix_reply_assistant_drafts_outbound_draft_id", "related_outbound_draft_id"),
        Index("ix_reply_assistant_drafts_updated_at", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
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
    related_delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("outreach_deliveries.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_outbound_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("outreach_drafts.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ReplyAssistantDraftStatus] = mapped_column(
        Enum(
            ReplyAssistantDraftStatus,
            name="replyassistantdraftstatus",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ReplyAssistantDraftStatus.GENERATED,
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    should_escalate_reviewer: Mapped[bool] = mapped_column(nullable=False, default=False)
    generator_role: Mapped[str] = mapped_column(String(50), nullable=False)
    generator_model: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    inbound_message: Mapped["InboundMessage"] = relationship(  # noqa: F821
        "InboundMessage", back_populates="reply_assistant_draft"
    )
    thread: Mapped["EmailThread | None"] = relationship(  # noqa: F821
        "EmailThread", back_populates="reply_assistant_drafts"
    )
    lead: Mapped["Lead | None"] = relationship("Lead", back_populates="reply_assistant_drafts")  # noqa: F821
    related_delivery: Mapped["OutreachDelivery | None"] = relationship(  # noqa: F821
        "OutreachDelivery", back_populates="reply_assistant_drafts"
    )
    related_outbound_draft: Mapped["OutreachDraft | None"] = relationship(  # noqa: F821
        "OutreachDraft", back_populates="reply_assistant_drafts"
    )
