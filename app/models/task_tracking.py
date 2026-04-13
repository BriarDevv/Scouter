from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.lead import Lead


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index("ix_pipeline_runs_lead_id", "lead_id"),
        Index("ix_pipeline_runs_status", "status"),
        Index("ix_pipeline_runs_root_task_id", "root_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    root_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    step_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lead: Mapped[Lead] = relationship("Lead", back_populates="pipeline_runs")  # noqa: F821
    tasks: Mapped[list[TaskRun]] = relationship(
        "TaskRun", back_populates="pipeline_run", cascade="all, delete-orphan"
    )


class TaskRun(Base):
    __tablename__ = "task_runs"
    __table_args__ = (
        Index("ix_task_runs_lead_id", "lead_id"),
        Index("ix_task_runs_pipeline_run_id", "pipeline_run_id"),
        Index("ix_task_runs_status", "status"),
        Index("ix_task_runs_task_name_scope_key", "task_name", "scope_key"),
    )

    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    queue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stop_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    lead: Mapped[Lead | None] = relationship("Lead")  # noqa: F821
    pipeline_run: Mapped[PipelineRun | None] = relationship("PipelineRun", back_populates="tasks")
