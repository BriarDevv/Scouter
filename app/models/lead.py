import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeadStatus(str, enum.Enum):
    NEW = "new"
    ENRICHED = "enriched"
    SCORED = "scored"
    QUALIFIED = "qualified"
    DRAFT_READY = "draft_ready"
    APPROVED = "approved"
    CONTACTED = "contacted"
    OPENED = "opened"
    REPLIED = "replied"
    MEETING = "meeting"
    WON = "won"
    LOST = "lost"
    SUPPRESSED = "suppressed"


class LeadQuality(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_email", "email", unique=False),
        Index("ix_leads_website_url", "website_url", unique=False),
        Index("ix_leads_status", "status"),
        Index("ix_leads_score", "score"),
        Index("ix_leads_status_score", "status", "score"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_llm_quality", "llm_quality"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str] = mapped_column(String(500), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_maps_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(nullable=True)
    business_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Source
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lead_sources.id", ondelete="SET NULL"), nullable=True
    )

    # Pipeline state
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), nullable=False, default=LeadStatus.NEW
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # LLM analysis
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    llm_quality_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_suggested_angle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dedup fingerprint (normalized: lowercase business_name + city + domain)
    dedup_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    source: Mapped["LeadSource"] = relationship("LeadSource", back_populates="leads")  # noqa: F821
    signals: Mapped[list["LeadSignal"]] = relationship(  # noqa: F821
        "LeadSignal", back_populates="lead", cascade="all, delete-orphan"
    )
    outreach_drafts: Mapped[list["OutreachDraft"]] = relationship(  # noqa: F821
        "OutreachDraft", back_populates="lead", cascade="all, delete-orphan"
    )
    outreach_deliveries: Mapped[list["OutreachDelivery"]] = relationship(  # noqa: F821
        "OutreachDelivery", back_populates="lead", cascade="all, delete-orphan"
    )
    email_threads: Mapped[list["EmailThread"]] = relationship(  # noqa: F821
        "EmailThread", back_populates="lead"
    )
    inbound_messages: Mapped[list["InboundMessage"]] = relationship(  # noqa: F821
        "InboundMessage", back_populates="lead"
    )
    reply_assistant_drafts: Mapped[list["ReplyAssistantDraft"]] = relationship(  # noqa: F821
        "ReplyAssistantDraft", back_populates="lead"
    )
    reply_assistant_sends: Mapped[list["ReplyAssistantSend"]] = relationship(  # noqa: F821
        "ReplyAssistantSend", back_populates="lead"
    )
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(  # noqa: F821
        "PipelineRun", back_populates="lead", cascade="all, delete-orphan"
    )

    @property
    def quality(self) -> LeadQuality:
        if self.score is None:
            return LeadQuality.UNKNOWN
        if self.score >= 60:
            return LeadQuality.HIGH
        if self.score >= 30:
            return LeadQuality.MEDIUM
        return LeadQuality.LOW
