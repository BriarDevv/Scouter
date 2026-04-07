"""Investigation thread — stores Scout agent's full tool call history per lead.

Each time Scout investigates a lead, the full sequence of tool calls,
pages visited, and findings is stored here. This enables:
- Dashboard visualization of Scout's investigation process
- Debugging and quality review of research quality
- Historical comparison of investigation approaches
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvestigationThread(Base):
    __tablename__ = "investigation_threads"
    __table_args__ = (
        Index("ix_investigation_threads_lead_id", "lead_id"),
        Index("ix_investigation_threads_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    agent_model: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_calls_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    pages_visited_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    findings_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    loops_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
