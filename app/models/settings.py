"""Operational settings — singleton row persisted in DB (id always = 1).

Non-secret, non-infra configuration editable from the dashboard.
Deploy-time config stays in environment variables. Runtime product policy lives
here. Secrets live in dedicated credential tables/services.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationalSettings(Base):
    __tablename__ = "operational_settings"
    __table_args__ = (CheckConstraint("id = 1", name="singleton_check"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # ── Brand / Signature
    brand_name: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_name: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_role: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_company: Mapped[str | None] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True)
    calendar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_cta: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_include_portfolio: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signature_is_solo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_outreach_tone: Mapped[str] = mapped_column(
        String, default="profesional", nullable=False
    )
    default_reply_tone: Mapped[str] = mapped_column(String, default="profesional", nullable=False)
    default_closing_line: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Mail outbound overrides (non-secret)
    mail_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mail_from_email: Mapped[str | None] = mapped_column(String, nullable=True)
    mail_from_name: Mapped[str | None] = mapped_column(String, nullable=True)
    mail_reply_to: Mapped[str | None] = mapped_column(String, nullable=True)
    mail_send_timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    require_approved_drafts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Mail inbound overrides (non-secret)
    mail_inbound_sync_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mail_inbound_mailbox: Mapped[str | None] = mapped_column(String, nullable=True)
    mail_inbound_sync_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mail_inbound_timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mail_inbound_search_criteria: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Rules / Automation
    auto_classify_inbound: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reply_assistant_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reviewer_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewer_labels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reviewer_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    prioritize_quote_replies: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prioritize_meeting_replies: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_reply_assistant_generation: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    use_reviewer_for_labels: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Notifications
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_score_threshold: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # ── WhatsApp alerts (non-secret config only; secrets in WhatsAppCredentials)
    whatsapp_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_min_severity: Mapped[str] = mapped_column(String, default="high", nullable=False)
    whatsapp_categories: Mapped[list] = mapped_column(
        JSON, default=lambda: ["business", "security"], nullable=False
    )
    # ── Telegram alerts (non-secret config; secrets in TelegramCredentials)
    telegram_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── WhatsApp outreach (draft generation in pipeline)
    whatsapp_outreach_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Hermes 3 agent routing per channel
    telegram_agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Runtime mode (safe | assisted | auto)
    runtime_mode: Mapped[str] = mapped_column(String, default="safe", nullable=False)

    # ── Auto pipeline trigger
    auto_pipeline_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # ── Resource mode — overrides LOW_RESOURCE_MODE env var when set
    low_resource_mode: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── Pricing matrix (JSON string for budget estimation)
    pricing_matrix: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Scoring overrides from batch review proposals (JSON: {signal_key: weight})
    scoring_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
