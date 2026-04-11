"""Integration credentials — singleton row persisted in DB (id always = 1).

Holds deploy-style secrets (currently Google Maps API key) that used to live
only in the .env file. Keeping them in a DB row lets the operator rotate or
replace them from the UI without restarting the backend, and protects against
accidental .env overwrites wiping the secrets silently.

Secrets are stored encrypted via `app.core.crypto.encrypt_if_needed` and
exposed via `decrypt_safe` on read. API responses never leak the raw value —
only a boolean "is set" flag and the last 4 chars for visual confirmation.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IntegrationCredentials(Base):
    __tablename__ = "integration_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Google Maps Places API (New) — consumed by app/crawlers/google_maps_crawler.py
    # Stored encrypted; read via get_effective_google_maps_key() which falls
    # back to settings.GOOGLE_MAPS_API_KEY (env) when the DB row is empty.
    google_maps_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_maps_api_key_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
