"""Territory performance snapshot — rolling window metrics per territory.

Stores a point-in-time aggregate of pipeline performance for a single
Territory. The Growth Intelligence Agent uses historical snapshots to detect
trends, identify over/under-performers, and decide which territories to
expand or retire.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.territory import Territory


class TerritoryPerformance(Base):
    __tablename__ = "territory_performance_snapshots"
    __table_args__ = (
        Index("ix_territory_performance_territory_id", "territory_id"),
        Index("ix_territory_performance_period_end", "period_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    territory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("territories.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    leads_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Reached QUALIFIED or DRAFT_READY or any later stage.
    leads_qualified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Reached CONTACTED or any later stage.
    leads_contacted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leads_lost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    conversion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    territory: Mapped[Territory] = relationship(  # noqa: F821
        "Territory", back_populates="performance_snapshots"
    )
