"""Structured reviewer corrections — enables aggregation and feedback loops.

Each time a reviewer evaluates a lead, draft, or brief, structured corrections
are extracted and stored here. Weekly aggregation surfaces patterns (e.g., "tone
too formal" appearing 12 times) that drive prompt improvements.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CorrectionCategory(str, enum.Enum):
    TONE = "tone"
    CTA = "cta"
    PERSONALIZATION = "personalization"
    LENGTH = "length"
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    FORMAT = "format"
    LANGUAGE = "language"


class CorrectionSeverity(str, enum.Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    SUGGESTION = "suggestion"


class ReviewCorrection(Base):
    __tablename__ = "review_corrections"
    __table_args__ = (
        Index("ix_review_corrections_lead_id", "lead_id"),
        Index("ix_review_corrections_category", "category"),
        Index("ix_review_corrections_created_at", "created_at"),
        Index("ix_review_corrections_review_type", "review_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    review_type: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[CorrectionCategory] = mapped_column(Enum(CorrectionCategory), nullable=False)
    severity: Mapped[CorrectionSeverity] = mapped_column(
        Enum(CorrectionSeverity), nullable=False, default=CorrectionSeverity.SUGGESTION
    )
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
