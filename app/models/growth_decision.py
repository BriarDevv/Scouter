"""Growth decision audit log — tracks every autonomous growth-agent decision."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GrowthDecisionLog(Base):
    __tablename__ = "growth_decision_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    action_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    leads_generated_7d: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversions_7d: Mapped[int | None] = mapped_column(Integer, nullable=True)
