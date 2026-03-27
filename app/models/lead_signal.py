import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SignalType(str, enum.Enum):
    NO_WEBSITE = "no_website"
    INSTAGRAM_ONLY = "instagram_only"
    OUTDATED_WEBSITE = "outdated_website"
    NO_CUSTOM_DOMAIN = "no_custom_domain"
    NO_VISIBLE_EMAIL = "no_visible_email"
    NO_SSL = "no_ssl"
    WEAK_SEO = "weak_seo"
    NO_MOBILE_FRIENDLY = "no_mobile_friendly"
    SLOW_LOAD = "slow_load"
    WEBSITE_ERROR = "website_error"
    HAS_WEBSITE = "has_website"
    HAS_CUSTOM_DOMAIN = "has_custom_domain"


class LeadSignal(Base):
    __tablename__ = "lead_signals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="signals")  # noqa: F821
