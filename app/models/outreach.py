import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DraftStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[DraftStatus] = mapped_column(
        Enum(DraftStatus), nullable=False, default=DraftStatus.PENDING_REVIEW
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="outreach_drafts")  # noqa: F821
    logs: Mapped[list["OutreachLog"]] = relationship(
        "OutreachLog", back_populates="draft", cascade="all, delete-orphan"
    )
    deliveries: Mapped[list["OutreachDelivery"]] = relationship(  # noqa: F821
        "OutreachDelivery", back_populates="draft", cascade="all, delete-orphan"
    )


class LogAction(str, enum.Enum):
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    OPENED = "opened"
    REPLIED = "replied"
    MEETING = "meeting"
    WON = "won"
    LOST = "lost"


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("outreach_drafts.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[LogAction] = mapped_column(Enum(LogAction), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    draft: Mapped[OutreachDraft | None] = relationship("OutreachDraft", back_populates="logs")
