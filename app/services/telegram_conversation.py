"""Telegram conversation handler -- query interface + controlled actions via Telegram Bot.

Reuses the intent detection, query handlers, and action executors from the
WhatsApp conversation module, but checks Telegram-specific settings flags
and uses Telegram-specific confirmation state.
"""

from __future__ import annotations

import time
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.logging import get_logger

# Reuse generic conversation logic from WhatsApp module
from app.services.whatsapp_conversation import (
    Intent,
    _ACTION_INTENTS,
    _sanitize,
    _check_rate_limit,
    _detect_intent,
    _query_leads,
    _query_lead_detail,
    _query_notifications,
    _query_drafts,
    _query_stats,
    _help_message,
    _get_action_description,
    _get_action_params,
    _execute_confirmed_action,
)

logger = get_logger(__name__)


def _is_actions_enabled(db: Session) -> bool:
    """Check if Telegram actions are enabled in operational settings."""
    from app.models.settings import OperationalSettings
    settings = db.get(OperationalSettings, 1)
    if settings is None:
        return False
    return bool(getattr(settings, "telegram_actions_enabled", False))


def handle_inbound_message(db: Session, chat_id: str, message: str) -> str:
    """Process an inbound Telegram message and return a text response.

    This is the main entry point called by the Telegram webhook endpoint.
    Handles both read-only queries and confirmed actions.
    """
    from app.services.telegram_confirmation import (
        cancel_pending,
        confirm_pending,
        create_pending,
        has_pending,
        is_locked,
        record_failed_confirmation,
    )
    from app.services.whatsapp_actions import check_action_rate_limit

    # Rate limit check (uses chat_id as identifier)
    if not _check_rate_limit(chat_id, db):
        logger.warning("tg_rate_limited", chat_id=chat_id[:6] + "***")
        return "Has superado el limite de mensajes (20 cada 15 min). Intenta mas tarde."

    # Sanitize input
    clean = _sanitize(message)
    if clean is None:
        logger.warning("tg_suspicious_input", chat_id=chat_id[:6] + "***")
        return "Mensaje rechazado por contenido no permitido."

    if not clean:
        return _help_message()

    # Check if chat is locked out from actions
    if is_locked(chat_id):
        logger.warning("tg_chat_locked_attempt", chat_id=chat_id[:6] + "***")
        return "Tu chat esta temporalmente bloqueado por intentos fallidos. Intenta en 15 minutos."

    # Check if there is a pending confirmation for this chat
    if has_pending(chat_id):
        normalized = clean.lower().strip()
        # Accept SI/si/yes
        if normalized in ("si", "sí", "yes"):
            action = confirm_pending(chat_id)
            if action is None:
                return "No hay accion pendiente o ya expiro."
            logger.info(
                "tg_action_confirmed",
                chat_id=chat_id[:6] + "***",
                intent=action.intent,
            )
            return _execute_confirmed_action(db, action.intent, action.params)
        # Accept NO/no
        if normalized in ("no",):
            cancelled = cancel_pending(chat_id)
            if cancelled:
                return "Accion cancelada."
            return "No hay accion pendiente."
        # Anything else while pending is a failed confirmation
        locked = record_failed_confirmation(chat_id)
        if locked:
            cancel_pending(chat_id)
            return "Demasiados intentos incorrectos. Chat bloqueado por 15 minutos."
        return "Responde *SI* para confirmar o *NO* para cancelar la accion pendiente."

    # Detect intent
    intent, extra = _detect_intent(clean)
    logger.info("tg_intent_detected", intent=intent.value, chat_id=chat_id[:6] + "***")

    # Handle action intents
    if intent in _ACTION_INTENTS:
        # Check if actions are enabled
        if not _is_actions_enabled(db):
            return "Las acciones via Telegram no estan habilitadas. Activalas desde Configuracion."

        # Check action rate limit
        if not check_action_rate_limit(chat_id):
            return "Has superado el limite de acciones (10 por hora). Intenta mas tarde."

        # Create pending confirmation
        description = _get_action_description(intent, extra)
        params = _get_action_params(intent, extra)
        return create_pending(
            chat_id=chat_id,
            intent=intent.value,
            params=params,
            description_es=description,
        )

    # Route to read-only handler
    if intent == Intent.QUERY_LEADS:
        return _query_leads(db)
    if intent == Intent.QUERY_LEAD_DETAIL:
        return _query_lead_detail(db, extra or "")
    if intent == Intent.QUERY_NOTIFICATIONS:
        return _query_notifications(db)
    if intent == Intent.QUERY_DRAFTS:
        return _query_drafts(db)
    if intent == Intent.QUERY_STATS:
        return _query_stats(db)

    # HELP — explicit help request
    if intent == Intent.HELP and clean.lower() in ("help", "ayuda", "?", "comandos"):
        return _help_message()

    # OpenClaw chat fallback — route unknown messages to AI
    from app.models.settings import OperationalSettings
    ops = db.get(OperationalSettings, 1)
    if ops and getattr(ops, "telegram_openclaw_enrichment", False):
        from app.services.openclaw_chat_service import chat_with_openclaw
        logger.info("tg_routing_to_openclaw", chat_id=chat_id[:6] + "***")
        return chat_with_openclaw(db, chat_id, clean)

    # Final fallback — show help with unknown command hint
    return _help_message(clean)
