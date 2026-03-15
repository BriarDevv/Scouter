"""Telegram credentials — singleton row persisted in DB (id always = 1).

Follows the same pattern as WhatsAppCredentials: secrets are write-only
and never exposed via API responses.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TelegramCredentials(Base):
    __tablename__ = "telegram_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Bot details
    bot_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bot_token: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Chat ID — the Telegram chat to send alerts to (obtained after /start)
    chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Webhook
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)

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
