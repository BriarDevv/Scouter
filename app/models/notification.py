"""Notification model — unified notifications for business, system, and security events."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NotificationCategory(str, enum.Enum):
    BUSINESS = "business"
    SYSTEM = "system"
    SECURITY = "security"


class NotificationSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_category", "category"),
        Index("ix_notifications_severity", "severity"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_type", "type"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_source", "source_kind", "source_id"),
        Index("uq_notifications_dedup_key", "dedup_key", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(
            NotificationCategory,
            name="notificationcategory",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(
            NotificationSeverity,
            name="notificationseverity",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus,
            name="notificationstatus",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
        default=NotificationStatus.UNREAD,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    channel_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dedup_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
