import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BudgetTier(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PREMIUM = "premium"


class EstimatedScope(str, enum.Enum):
    LANDING = "landing"
    INSTITUTIONAL_WEB = "institutional_web"
    CATALOG = "catalog"
    ECOMMERCE = "ecommerce"
    REDESIGN = "redesign"
    AUTOMATION = "automation"
    BRANDING_WEB = "branding_web"


class ContactMethod(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    CALL = "call"
    DEMO_FIRST = "demo_first"
    MANUAL_REVIEW = "manual_review"


class CallDecision(str, enum.Enum):
    YES = "yes"
    NO = "no"
    MAYBE = "maybe"


class ContactPriority(str, enum.Enum):
    IMMEDIATE = "immediate"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class BriefStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    FAILED = "failed"


class CommercialBrief(Base):
    __tablename__ = "commercial_briefs"
    __table_args__ = (Index("ix_commercial_briefs_research_report_id", "research_report_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("leads.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    research_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("lead_research_reports.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[BriefStatus] = mapped_column(
        Enum(BriefStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BriefStatus.PENDING,
    )
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_tier: Mapped[BudgetTier | None] = mapped_column(
        Enum(BudgetTier, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    estimated_budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_scope: Mapped[EstimatedScope | None] = mapped_column(
        Enum(EstimatedScope, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    recommended_contact_method: Mapped[ContactMethod | None] = mapped_column(
        Enum(ContactMethod, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    should_call: Mapped[CallDecision | None] = mapped_column(
        Enum(CallDecision, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    call_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_this_lead_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_business_signals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    main_digital_gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommended_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    demo_recommended: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    contact_priority: Mapped[ContactPriority | None] = mapped_column(
        Enum(ContactPriority, values_callable=lambda x: [e.value for e in x]), nullable=True
    )

    generator_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewer_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    lead: Mapped["Lead"] = relationship(  # noqa: F821
        "Lead", back_populates="commercial_briefs"
    )
    research_report: Mapped["LeadResearchReport"] = relationship(  # noqa: F821
        "LeadResearchReport"
    )
