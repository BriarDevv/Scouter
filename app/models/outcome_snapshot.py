"""Outcome snapshot — captures pipeline state when a lead reaches WON or LOST.

When a lead transitions to a terminal outcome, we freeze:
- The lead's score and quality rating at that point
- The signals that were detected
- The full pipeline context (from step_context_json)
- The channel/approach used for outreach

This enables Phase 4 outcome-based learning: correlating pipeline decisions
with actual commercial results.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OutcomeSnapshot(Base):
    __tablename__ = "outcome_snapshots"
    __table_args__ = (
        Index("ix_outcome_snapshots_lead_id", "lead_id"),
        Index("ix_outcome_snapshots_outcome", "outcome"),
        Index("ix_outcome_snapshots_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)

    # Snapshot of pipeline decisions at time of outcome
    lead_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lead_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signals_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pipeline_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    draft_channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewer_verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    corrections_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
