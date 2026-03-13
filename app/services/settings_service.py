from app.core.config import settings
from app.llm.catalog import DEFAULT_ROLE_MODEL_MAP
from app.llm.roles import LLMRole
from app.services.inbound_mail_service import get_inbound_sync_status


def get_llm_settings() -> dict:
    executor_override = (settings.OLLAMA_EXECUTOR_MODEL or "").strip()

    return {
        "provider": "ollama",
        "base_url": settings.OLLAMA_BASE_URL,
        "read_only": True,
        "editable": False,
        "leader_model": settings.ollama_leader_model,
        "executor_model": settings.ollama_executor_model,
        "reviewer_model": settings.ollama_reviewer_model,
        "supported_models": list(settings.ollama_supported_models),
        "default_role_models": {
            "leader": DEFAULT_ROLE_MODEL_MAP[LLMRole.LEADER],
            "executor": DEFAULT_ROLE_MODEL_MAP[LLMRole.EXECUTOR],
            "reviewer": DEFAULT_ROLE_MODEL_MAP[LLMRole.REVIEWER],
        },
        "legacy_executor_fallback_model": settings.OLLAMA_MODEL.strip(),
        "legacy_executor_fallback_active": not executor_override,
        "timeout_seconds": settings.OLLAMA_TIMEOUT,
        "max_retries": settings.OLLAMA_MAX_RETRIES,
    }


def get_mail_settings(db) -> dict:
    last_sync = get_inbound_sync_status(db)

    outbound_missing = []
    if not (settings.MAIL_FROM_EMAIL or "").strip():
        outbound_missing.append("MAIL_FROM_EMAIL")
    if not (settings.MAIL_SMTP_HOST or "").strip():
        outbound_missing.append("MAIL_SMTP_HOST")
    if not (settings.MAIL_SMTP_USERNAME or "").strip():
        outbound_missing.append("MAIL_SMTP_USERNAME")
    if not (settings.MAIL_SMTP_PASSWORD or "").strip():
        outbound_missing.append("MAIL_SMTP_PASSWORD")

    inbound_missing = []
    if not (settings.MAIL_IMAP_HOST or "").strip():
        inbound_missing.append("MAIL_IMAP_HOST")
    if not (settings.MAIL_IMAP_USERNAME or "").strip():
        inbound_missing.append("MAIL_IMAP_USERNAME")
    if not (settings.MAIL_IMAP_PASSWORD or "").strip():
        inbound_missing.append("MAIL_IMAP_PASSWORD")

    outbound_configured = not outbound_missing
    inbound_configured = not inbound_missing
    outbound_ready = settings.MAIL_ENABLED and outbound_configured
    inbound_ready = settings.MAIL_INBOUND_ENABLED and inbound_configured

    last_sync_payload = None
    if last_sync:
        last_sync_payload = {
            "status": last_sync.status,
            "at": last_sync.completed_at.isoformat() if last_sync.completed_at else last_sync.started_at.isoformat(),
            "counts": {
                "fetched": last_sync.fetched_count,
                "new": last_sync.new_count,
                "deduplicated": last_sync.deduplicated_count,
                "matched": last_sync.matched_count,
                "unmatched": last_sync.unmatched_count,
            },
            "error": last_sync.error,
        }

    return {
        "read_only": True,
        "editable": False,
        "outbound": {
            "enabled": settings.MAIL_ENABLED,
            "provider": settings.MAIL_PROVIDER.lower(),
            "configured": outbound_configured,
            "ready": outbound_ready,
            "from_email": (settings.MAIL_FROM_EMAIL or "").strip() or None,
            "from_name": settings.MAIL_FROM_NAME.strip(),
            "reply_to": (settings.MAIL_REPLY_TO or "").strip() or None,
            "send_timeout_seconds": settings.MAIL_SEND_TIMEOUT,
            "require_approved_drafts": True,
            "missing_requirements": outbound_missing,
        },
        "inbound": {
            "enabled": settings.MAIL_INBOUND_ENABLED,
            "provider": settings.MAIL_INBOUND_PROVIDER.lower(),
            "configured": inbound_configured,
            "ready": inbound_ready,
            "account": (settings.MAIL_IMAP_USERNAME or "").strip() or None,
            "mailbox": settings.MAIL_IMAP_MAILBOX.strip(),
            "sync_limit": settings.MAIL_INBOUND_SYNC_LIMIT,
            "timeout_seconds": settings.MAIL_INBOUND_TIMEOUT,
            "search_criteria": settings.MAIL_IMAP_SEARCH_CRITERIA.strip(),
            "auto_classify_inbound": settings.MAIL_AUTO_CLASSIFY_INBOUND,
            "use_reviewer_for_labels": list(settings.mail_use_reviewer_for_labels),
            "last_sync": last_sync_payload,
            "missing_requirements": inbound_missing,
        },
        "health": {
            "configured": outbound_configured or inbound_configured,
            "enabled": settings.MAIL_ENABLED or settings.MAIL_INBOUND_ENABLED,
            "outbound_ready": outbound_ready,
            "inbound_ready": inbound_ready,
            "last_sync_status": last_sync.status if last_sync else None,
            "last_sync_at": (
                last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None
            ),
        },
    }
