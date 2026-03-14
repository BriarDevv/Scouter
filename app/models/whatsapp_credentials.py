"""WhatsApp credentials — singleton row persisted in DB (id always = 1).

Follows the same pattern as MailCredentials: secrets are write-only
and never exposed via API responses.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WhatsAppCredentials(Base):
    __tablename__ = "whatsapp_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Provider selection
    provider: Mapped[str] = mapped_column(String(50), default="callmebot", nullable=False)

    # Connection details
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Test results
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
