"""Operational settings service — singleton CRUD + effective value resolution."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings as env
from app.core.logging import get_logger
from app.models.settings import OperationalSettings

logger = get_logger(__name__)

_SINGLETON_ID = 1


def get_or_create(db: Session) -> OperationalSettings:
    """Return the singleton row, creating it with defaults if it doesn't exist."""
    row = db.get(OperationalSettings, _SINGLETON_ID)
    if row is None:
        row = OperationalSettings(id=_SINGLETON_ID)
        db.add(row)
        db.flush()
        db.refresh(row)
        logger.info("operational_settings_created")
    return row


def get_cached_settings(db: Session) -> OperationalSettings:
    """Return settings cached for this DB session to avoid repeated lookups."""
    cache_key = "_operational_settings_cache"
    cached = db.info.get(cache_key)
    if cached is not None:
        return cached
    settings = get_or_create(db)
    db.info[cache_key] = settings
    return settings


_ALLOWED_SETTINGS_FIELDS = {
    "brand_name", "signature_name", "signature_role", "signature_company",
    "portfolio_url", "website_url", "calendar_url", "signature_cta",
    "signature_include_portfolio", "signature_is_solo",
    "default_outreach_tone", "default_reply_tone", "default_closing_line",
    "mail_enabled", "mail_from_email", "mail_from_name", "mail_reply_to",
    "mail_send_timeout_seconds", "require_approved_drafts",
    "mail_inbound_sync_enabled", "mail_inbound_mailbox", "mail_inbound_sync_limit",
    "mail_inbound_timeout_seconds", "mail_inbound_search_criteria",
    "auto_classify_inbound", "reply_assistant_enabled",
    "reviewer_enabled", "reviewer_labels", "reviewer_confidence_threshold",
    "prioritize_quote_replies", "prioritize_meeting_replies",
    "allow_reply_assistant_generation",
    "use_reviewer_for_labels",
    "notifications_enabled", "notification_score_threshold",
    "whatsapp_alerts_enabled", "whatsapp_min_severity", "whatsapp_categories",
    "telegram_alerts_enabled", "whatsapp_outreach_enabled",
    "telegram_agent_enabled", "whatsapp_agent_enabled",
    "runtime_mode", "pricing_matrix",
    "low_resource_mode",
}


def update_operational_settings(db: Session, updates: dict) -> OperationalSettings:
    """Partial update. Only touches fields present in updates."""
    row = get_or_create(db)
    for key, value in updates.items():
        if key in _ALLOWED_SETTINGS_FIELDS:
            setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    db.refresh(row)
    logger.info("operational_settings_updated", fields=list(updates.keys()))
    return row


_RUNTIME_MODE_PRESETS = {
    "safe": {
        "require_approved_drafts": True,
        "auto_classify_inbound": False,
        "reply_assistant_enabled": False,
        "reviewer_enabled": False,
        "whatsapp_outreach_enabled": False,
    },
    "assisted": {
        "require_approved_drafts": True,
        "auto_classify_inbound": True,
        "reply_assistant_enabled": True,
        "reviewer_enabled": True,
        "whatsapp_outreach_enabled": False,
    },
    "auto": {
        "require_approved_drafts": False,
        "auto_classify_inbound": True,
        "reply_assistant_enabled": True,
        "reviewer_enabled": True,
        "whatsapp_outreach_enabled": True,
    },
}


def apply_runtime_mode(db: Session, mode: str) -> OperationalSettings:
    """Apply a runtime mode preset, setting multiple toggles atomically."""
    if mode not in _RUNTIME_MODE_PRESETS:
        raise ValueError(f"Invalid runtime mode: {mode}. Must be one of: safe, assisted, auto")
    updates = {**_RUNTIME_MODE_PRESETS[mode], "runtime_mode": mode}
    return update_operational_settings(db, updates)


def _eff(db_val, env_val):
    """Return db_val if not None, else env_val."""
    return db_val if db_val is not None else env_val


def get_effective_mail_outbound(row: OperationalSettings) -> dict:
    return {
        "enabled": _eff(row.mail_enabled, env.MAIL_ENABLED),
        "from_email": _eff(row.mail_from_email, env.MAIL_FROM_EMAIL),
        "from_name": _eff(row.mail_from_name, env.MAIL_FROM_NAME),
        "reply_to": _eff(row.mail_reply_to, env.MAIL_REPLY_TO),
        "send_timeout_seconds": _eff(row.mail_send_timeout_seconds, env.MAIL_SEND_TIMEOUT),
        "require_approved_drafts": row.require_approved_drafts,
    }


def get_effective_mail_inbound(row: OperationalSettings) -> dict:
    return {
        "sync_enabled": _eff(row.mail_inbound_sync_enabled, env.MAIL_INBOUND_ENABLED),
        "mailbox": _eff(row.mail_inbound_mailbox, env.MAIL_IMAP_MAILBOX),
        "sync_limit": _eff(row.mail_inbound_sync_limit, env.MAIL_INBOUND_SYNC_LIMIT),
        "timeout_seconds": _eff(row.mail_inbound_timeout_seconds, env.MAIL_INBOUND_TIMEOUT),
        "search_criteria": _eff(row.mail_inbound_search_criteria, env.MAIL_IMAP_SEARCH_CRITERIA),
        "auto_classify_inbound": row.auto_classify_inbound,
        "use_reviewer_for_labels": row.use_reviewer_for_labels or list(env.mail_use_reviewer_for_labels),
    }


def get_brand_context(db: Session) -> dict:
    """Return brand/signature context dict for use in LLM prompts."""
    row = get_or_create(db)
    return {
        "brand_name": row.brand_name,
        "signature_name": row.signature_name,
        "signature_role": row.signature_role,
        "signature_company": row.signature_company,
        "portfolio_url": row.portfolio_url,
        "website_url": row.website_url,
        "calendar_url": row.calendar_url,
        "signature_cta": row.signature_cta,
        "signature_include_portfolio": row.signature_include_portfolio,
        "signature_is_solo": row.signature_is_solo,
        "default_outreach_tone": row.default_outreach_tone,
        "default_reply_tone": row.default_reply_tone,
        "default_closing_line": row.default_closing_line,
    }


def get_effective_rules(db: Session) -> dict:
    """Return rules/automation settings dict."""
    row = get_or_create(db)
    return {
        "require_approved_drafts": row.require_approved_drafts,
        "auto_classify_inbound": row.auto_classify_inbound,
        "reply_assistant_enabled": row.reply_assistant_enabled,
        "reviewer_enabled": row.reviewer_enabled,
        "reviewer_labels": row.reviewer_labels or [],
        "reviewer_confidence_threshold": row.reviewer_confidence_threshold,
        "prioritize_quote_replies": row.prioritize_quote_replies,
        "prioritize_meeting_replies": row.prioritize_meeting_replies,
        "allow_reply_assistant_generation": row.allow_reply_assistant_generation,
        "use_reviewer_for_labels": row.use_reviewer_for_labels or [],
        "notifications_enabled": row.notifications_enabled,
        "notification_score_threshold": row.notification_score_threshold,
        "whatsapp_alerts_enabled": row.whatsapp_alerts_enabled,
        "whatsapp_min_severity": row.whatsapp_min_severity,
        "whatsapp_categories": row.whatsapp_categories or [],
        "whatsapp_outreach_enabled": row.whatsapp_outreach_enabled,
        "telegram_agent_enabled": row.telegram_agent_enabled,
        "whatsapp_agent_enabled": row.whatsapp_agent_enabled,
    }


def to_response_dict(row: OperationalSettings) -> dict:
    """Serialize the singleton for API response."""
    return {
        "id": row.id,
        "brand_name": row.brand_name,
        "signature_name": row.signature_name,
        "signature_role": row.signature_role,
        "signature_company": row.signature_company,
        "portfolio_url": row.portfolio_url,
        "website_url": row.website_url,
        "calendar_url": row.calendar_url,
        "signature_cta": row.signature_cta,
        "signature_include_portfolio": row.signature_include_portfolio,
        "signature_is_solo": row.signature_is_solo,
        "default_outreach_tone": row.default_outreach_tone,
        "default_reply_tone": row.default_reply_tone,
        "default_closing_line": row.default_closing_line,
        "mail_enabled": row.mail_enabled,
        "mail_from_email": row.mail_from_email,
        "mail_from_name": row.mail_from_name,
        "mail_reply_to": row.mail_reply_to,
        "mail_send_timeout_seconds": row.mail_send_timeout_seconds,
        "require_approved_drafts": row.require_approved_drafts,
        "mail_inbound_sync_enabled": row.mail_inbound_sync_enabled,
        "mail_inbound_mailbox": row.mail_inbound_mailbox,
        "mail_inbound_sync_limit": row.mail_inbound_sync_limit,
        "mail_inbound_timeout_seconds": row.mail_inbound_timeout_seconds,
        "mail_inbound_search_criteria": row.mail_inbound_search_criteria,
        "auto_classify_inbound": row.auto_classify_inbound,
        "reply_assistant_enabled": row.reply_assistant_enabled,
        "reviewer_enabled": row.reviewer_enabled,
        "reviewer_labels": row.reviewer_labels or [],
        "reviewer_confidence_threshold": row.reviewer_confidence_threshold,
        "prioritize_quote_replies": row.prioritize_quote_replies,
        "prioritize_meeting_replies": row.prioritize_meeting_replies,
        "allow_reply_assistant_generation": row.allow_reply_assistant_generation,
        "use_reviewer_for_labels": row.use_reviewer_for_labels or [],
        "notifications_enabled": row.notifications_enabled,
        "notification_score_threshold": row.notification_score_threshold,
        "whatsapp_alerts_enabled": row.whatsapp_alerts_enabled,
        "whatsapp_min_severity": row.whatsapp_min_severity,
        "whatsapp_categories": row.whatsapp_categories or [],
        "telegram_alerts_enabled": row.telegram_alerts_enabled,
        "whatsapp_outreach_enabled": row.whatsapp_outreach_enabled,
        "telegram_agent_enabled": row.telegram_agent_enabled,
        "whatsapp_agent_enabled": row.whatsapp_agent_enabled,
        "low_resource_mode": row.low_resource_mode,
        "runtime_mode": row.runtime_mode,
        "pricing_matrix": row.pricing_matrix,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
