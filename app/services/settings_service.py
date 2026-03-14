from app.core.config import settings
from app.llm.catalog import DEFAULT_ROLE_MODEL_MAP
from app.llm.roles import LLMRole
from app.services.inbound_mail_service import get_inbound_sync_status
from app.services.operational_settings_service import (
    get_effective_mail_inbound,
    get_effective_mail_outbound,
    get_or_create as get_operational_settings,
)


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
    op = get_operational_settings(db)
    outbound = get_effective_mail_outbound(op)
    inbound = get_effective_mail_inbound(op)

    # Credential presence (sensitive env vars)
    outbound_missing = []
    if not (settings.MAIL_FROM_EMAIL or "").strip() and not outbound["from_email"]:
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
    outbound_ready = outbound["enabled"] and outbound_configured
    inbound_ready = inbound["sync_enabled"] and inbound_configured

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
        "read_only": False,
        "editable": True,
        "outbound": {
            "enabled": outbound["enabled"],
            "provider": settings.MAIL_PROVIDER.lower(),
            "configured": outbound_configured,
            "ready": outbound_ready,
            "from_email": (outbound["from_email"] or "").strip() or None,
            "from_name": (outbound["from_name"] or "").strip(),
            "reply_to": (outbound["reply_to"] or "").strip() or None,
            "send_timeout_seconds": outbound["send_timeout_seconds"],
            "require_approved_drafts": outbound["require_approved_drafts"],
            "missing_requirements": outbound_missing,
        },
        "inbound": {
            "enabled": inbound["sync_enabled"],
            "provider": settings.MAIL_INBOUND_PROVIDER.lower(),
            "configured": inbound_configured,
            "ready": inbound_ready,
            "account": (settings.MAIL_IMAP_USERNAME or "").strip() or None,
            "mailbox": inbound["mailbox"].strip(),
            "sync_limit": inbound["sync_limit"],
            "timeout_seconds": inbound["timeout_seconds"],
            "search_criteria": inbound["search_criteria"].strip(),
            "auto_classify_inbound": inbound["auto_classify_inbound"],
            "use_reviewer_for_labels": inbound["use_reviewer_for_labels"],
            "last_sync": last_sync_payload,
            "missing_requirements": inbound_missing,
        },
        "health": {
            "configured": outbound_configured or inbound_configured,
            "enabled": outbound["enabled"] or inbound["sync_enabled"],
            "outbound_ready": outbound_ready,
            "inbound_ready": inbound_ready,
            "last_sync_status": last_sync.status if last_sync else None,
            "last_sync_at": (
                last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None
            ),
        },
    }
