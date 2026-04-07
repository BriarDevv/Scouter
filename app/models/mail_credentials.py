"""Mail credentials — singleton row (id always = 1).

Stores SMTP/IMAP connection details editable from the dashboard.
Passwords are encrypted via Fernet (app.core.crypto) on write; never exposed via API.
Resolution order for the mail providers: DB > .env fallback.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MailCredentials(Base):
    __tablename__ = "mail_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # ── SMTP ──────────────────────────────────────────────────────────
    smtp_host: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    smtp_username: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_ssl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    smtp_starttls: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── IMAP ──────────────────────────────────────────────────────────
    imap_host: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_port: Mapped[int] = mapped_column(Integer, default=993, nullable=False)
    imap_username: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_password: Mapped[str | None] = mapped_column(String, nullable=True)
    imap_ssl: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Last test results ─────────────────────────────────────────────
    smtp_last_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    smtp_last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    smtp_last_test_error: Mapped[str | None] = mapped_column(String, nullable=True)

    imap_last_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    imap_last_test_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    imap_last_test_error: Mapped[str | None] = mapped_column(String, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
