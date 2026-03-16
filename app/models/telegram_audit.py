"""Telegram audit log — append-only record of all inbound/outbound messages."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TelegramDirection(str, enum.Enum):
    INBOUND = "in"
    OUTBOUND = "out"


class TelegramAuditLog(Base):
    __tablename__ = "telegram_audit_log"
    __table_args__ = (
        Index("ix_tg_audit_chat_id", "chat_id"),
        Index("ix_tg_audit_direction", "direction"),
        Index("ix_tg_audit_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    direction: Mapped[TelegramDirection] = mapped_column(
        Enum(
            TelegramDirection,
            name="telegramdirection",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
