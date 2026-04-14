"""Territory model — groups cities into named territories for geographic analysis."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.territory_performance import TerritoryPerformance


class Territory(Base):
    __tablename__ = "territories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")
    cities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Geo scoping — used by the Google Places crawler to scope query results
    # to the intended country. country_code defaults to AR for legacy rows.
    # center_lat/lng enable locationBias.circle; bbox enables stricter
    # locationRestriction.rectangle (shape: {"sw": {"lat","lng"}, "ne": {"lat","lng"}}).
    country_code: Mapped[str] = mapped_column(
        String(2), default="AR", server_default="AR", nullable=False
    )
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_dup_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    crawl_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_saturated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    performance_snapshots: Mapped[list[TerritoryPerformance]] = relationship(  # noqa: F821
        "TerritoryPerformance",
        back_populates="territory",
        cascade="all, delete-orphan",
    )
