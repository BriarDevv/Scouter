"""Pydantic schemas for operational settings."""

from pydantic import BaseModel, field_validator


class OperationalSettingsUpdate(BaseModel):
    """Partial update — all fields optional. None means keep current value."""

    brand_name: str | None = None
    signature_name: str | None = None
    signature_role: str | None = None
    signature_company: str | None = None
    portfolio_url: str | None = None
    website_url: str | None = None
    calendar_url: str | None = None
    signature_cta: str | None = None
    signature_include_portfolio: bool | None = None
    signature_is_solo: bool | None = None
    default_outreach_tone: str | None = None
    default_reply_tone: str | None = None
    default_closing_line: str | None = None
    mail_enabled: bool | None = None
    mail_from_email: str | None = None
    mail_from_name: str | None = None
    mail_reply_to: str | None = None
    mail_send_timeout_seconds: int | None = None
    require_approved_drafts: bool | None = None
    mail_inbound_sync_enabled: bool | None = None
    mail_inbound_mailbox: str | None = None
    mail_inbound_sync_limit: int | None = None
    mail_inbound_timeout_seconds: int | None = None
    mail_inbound_search_criteria: str | None = None
    auto_classify_inbound: bool | None = None
    reply_assistant_enabled: bool | None = None
    reviewer_enabled: bool | None = None
    reviewer_labels: list[str] | None = None
    reviewer_confidence_threshold: float | None = None
    prioritize_quote_replies: bool | None = None
    prioritize_meeting_replies: bool | None = None
    allow_openclaw_briefs: bool | None = None
    allow_reply_assistant_generation: bool | None = None
    use_reviewer_for_labels: list[str] | None = None

    # Notifications & WhatsApp
    notifications_enabled: bool | None = None
    notification_score_threshold: int | None = None
    whatsapp_alerts_enabled: bool | None = None
    whatsapp_min_severity: str | None = None
    whatsapp_categories: list[str] | None = None
    # Telegram
    telegram_alerts_enabled: bool | None = None

    # Hermes 3 agent per channel
    telegram_agent_enabled: bool | None = None
    whatsapp_agent_enabled: bool | None = None

    @field_validator("reviewer_confidence_threshold")
    @classmethod
    def validate_threshold(cls, v):
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("reviewer_confidence_threshold must be between 0 and 1")
        return v

    # Non-nullable DB columns — can never be set to None from PATCH
    _NON_NULLABLE: frozenset = frozenset({
        "require_approved_drafts", "auto_classify_inbound", "reply_assistant_enabled",
        "reviewer_enabled", "signature_include_portfolio", "signature_is_solo", "prioritize_quote_replies",
        "prioritize_meeting_replies", "allow_openclaw_briefs", "allow_reply_assistant_generation",
        "reviewer_confidence_threshold",
        "notifications_enabled", "notification_score_threshold",
        "whatsapp_alerts_enabled",
        "telegram_alerts_enabled",
        "telegram_agent_enabled", "whatsapp_agent_enabled",
    })

    def to_update_dict(self) -> dict:
        """Return fields explicitly included in the request body.

        Uses model_fields_set (Pydantic v2) so that:
        - field not sent -> excluded (no accidental overwrite)
        - field sent as null -> included as None (allows clearing nullable string fields)
        - field sent as false/0/[] -> included (correct for booleans and numbers)
        Non-nullable DB columns (bool/float with DB defaults) skip null assignments.
        """
        dumped = self.model_dump()
        return {
            k: dumped[k]
            for k in self.model_fields_set
            if not (dumped[k] is None and k in self._NON_NULLABLE)
        }


class OperationalSettingsResponse(BaseModel):
    id: int
    brand_name: str | None
    signature_name: str | None
    signature_role: str | None
    signature_company: str | None
    portfolio_url: str | None
    website_url: str | None
    calendar_url: str | None
    signature_cta: str | None
    signature_include_portfolio: bool
    signature_is_solo: bool
    default_outreach_tone: str
    default_reply_tone: str
    default_closing_line: str | None
    mail_enabled: bool | None
    mail_from_email: str | None
    mail_from_name: str | None
    mail_reply_to: str | None
    mail_send_timeout_seconds: int | None
    require_approved_drafts: bool
    mail_inbound_sync_enabled: bool | None
    mail_inbound_mailbox: str | None
    mail_inbound_sync_limit: int | None
    mail_inbound_timeout_seconds: int | None
    mail_inbound_search_criteria: str | None
    auto_classify_inbound: bool
    reply_assistant_enabled: bool
    reviewer_enabled: bool
    reviewer_labels: list[str]
    reviewer_confidence_threshold: float
    prioritize_quote_replies: bool
    prioritize_meeting_replies: bool
    allow_openclaw_briefs: bool
    allow_reply_assistant_generation: bool
    use_reviewer_for_labels: list[str]
    notifications_enabled: bool
    notification_score_threshold: int
    whatsapp_alerts_enabled: bool
    whatsapp_min_severity: str
    whatsapp_categories: list[str]
    telegram_alerts_enabled: bool
    telegram_agent_enabled: bool
    whatsapp_agent_enabled: bool
    updated_at: str | None


class CredentialStatusItem(BaseModel):
    key: str
    label: str
    set: bool
    required: bool


class CredentialsStatusResponse(BaseModel):
    smtp: list[CredentialStatusItem]
    imap: list[CredentialStatusItem]
    all_smtp_ready: bool
    all_imap_ready: bool
