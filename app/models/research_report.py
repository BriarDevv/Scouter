import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ResearchStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceLevel(str, enum.Enum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    UNKNOWN = "unknown"
    MISMATCH = "mismatch"


class LeadResearchReport(Base):
    __tablename__ = "lead_research_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[ResearchStatus] = mapped_column(
        Enum(ResearchStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ResearchStatus.PENDING,
    )

    # Website analysis
    website_exists: Mapped[bool | None] = mapped_column(nullable=True)
    website_url_verified: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_confidence: Mapped[ConfidenceLevel | None] = mapped_column(
        Enum(ConfidenceLevel, values_callable=lambda x: [e.value for e in x]), nullable=True
    )

    # Instagram analysis
    instagram_exists: Mapped[bool | None] = mapped_column(nullable=True)
    instagram_url_verified: Mapped[str | None] = mapped_column(Text, nullable=True)
    instagram_confidence: Mapped[ConfidenceLevel | None] = mapped_column(
        Enum(ConfidenceLevel, values_callable=lambda x: [e.value for e in x]), nullable=True
    )

    # WhatsApp detection
    whatsapp_detected: Mapped[bool | None] = mapped_column(nullable=True)
    whatsapp_confidence: Mapped[ConfidenceLevel | None] = mapped_column(
        Enum(ConfidenceLevel, values_callable=lambda x: [e.value for e in x]), nullable=True
    )

    # Rich data
    screenshots_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    detected_signals_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    html_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # LLM-generated
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    researcher_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Timing
    research_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    lead: Mapped["Lead"] = relationship(  # noqa: F821
        "Lead", back_populates="research_reports"
    )
