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
        db.commit()
        db.refresh(row)
        logger.info("operational_settings_created")
    return row


def update_operational_settings(db: Session, updates: dict) -> OperationalSettings:
    """Partial update. Only touches fields present in updates."""
    row = get_or_create(db)
    for key, value in updates.items():
        if hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    logger.info("operational_settings_updated", fields=list(updates.keys()))
    return row


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
        "use_reviewer_for_labels": row.use_reviewer_for_labels or [],
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
        "allow_openclaw_briefs": row.allow_openclaw_briefs,
        "allow_reply_assistant_generation": row.allow_reply_assistant_generation,
        "use_reviewer_for_labels": row.use_reviewer_for_labels or [],
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
        "allow_openclaw_briefs": row.allow_openclaw_briefs,
        "allow_reply_assistant_generation": row.allow_reply_assistant_generation,
        "use_reviewer_for_labels": row.use_reviewer_for_labels or [],
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
