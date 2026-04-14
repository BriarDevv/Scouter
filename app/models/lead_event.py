"""LeadEvent — immutable audit log of a lead's journey through the pipeline.

Each row is a single observation (status transition, pipeline step success,
outreach send, manual override). Rows never mutate; the timeline is the
append-only history you replay for forensic debugging or analytics.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LeadEvent(Base):
    __tablename__ = "lead_events"
    __table_args__ = (
        Index("ix_lead_events_lead_id_created_at_desc", "lead_id", "created_at"),
        Index("ix_lead_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actor: Mapped[str] = mapped_column(
        String(64), nullable=False, default="system", server_default="system"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
