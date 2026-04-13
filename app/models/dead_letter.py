from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeadLetterTask(Base):
    __tablename__ = "dead_letter_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
