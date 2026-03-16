"""Telegram webhook — inbound message endpoint for conversational queries.

Receives Telegram Bot API Update objects, extracts chat_id + text,
validates the webhook secret, processes via conversation handler,
sends response back via Telegram sendMessage API, and audits.
"""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.logging import get_logger
from app.models.settings import OperationalSettings
from app.services.telegram_audit import log_inbound, log_outbound
from app.services.telegram_conversation import (
    Intent,
    _detect_intent,
    _sanitize,
    handle_inbound_message,
)
from app.services.telegram_service import send_message as tg_send_message

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramWebhookResponse(BaseModel):
    ok: bool


def _get_settings(db: Session) -> OperationalSettings:
    """Retrieve the singleton operational settings row."""
    row = db.get(OperationalSettings, 1)
    if not row:
        row = OperationalSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.post("/webhook", response_model=TelegramWebhookResponse)
def webhook_inbound(
    request: Request,
    body: dict[str, Any],
    db: Session = Depends(get_session),
    x_telegram_bot_api_secret_token: str = Header("", alias="X-Telegram-Bot-Api-Secret-Token"),
) -> TelegramWebhookResponse:
    """Receive inbound Telegram Bot API updates and return conversational response.

    Telegram sends Updates as JSON POST to this endpoint.
    Must return 200 quickly — Telegram retries on failure.
    """
    # Extract message from update
    message_obj = body.get("message") or body.get("edited_message")
    if not message_obj:
        # Not a text message update (could be callback_query, etc.) — acknowledge
        return TelegramWebhookResponse(ok=True)

    text = message_obj.get("text", "")
    chat = message_obj.get("chat", {})
    chat_id = str(chat.get("id", ""))

    if not text or not chat_id:
        return TelegramWebhookResponse(ok=True)

    # Validate webhook secret — check DB first, fall back to env var
    from app.models.telegram_credentials import TelegramCredentials
    tg_creds = db.get(TelegramCredentials, 1)
    webhook_secret = (
        (tg_creds.webhook_secret if tg_creds and tg_creds.webhook_secret else None)
        or os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    )
    if not webhook_secret or x_telegram_bot_api_secret_token != webhook_secret:
        logger.warning("tg_webhook_auth_failed", chat_id=chat_id[:6] + "***")
        raise HTTPException(status_code=403, detail="Webhook secret invalido.")

    # Check feature flag
    settings = _get_settings(db)
    if not settings.telegram_conversational_enabled:
        logger.info("tg_conversational_disabled")
        raise HTTPException(
            status_code=403,
            detail="La funcion de Telegram conversacional no esta habilitada.",
        )

    # Process message
    start = time.monotonic()
    response_text = handle_inbound_message(db, chat_id, text)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Detect intent for audit
    clean = _sanitize(text)
    intent_name: str | None = None
    if clean:
        intent, _ = _detect_intent(clean)
        intent_name = intent.value

    # Audit log
    log_inbound(db, chat_id, text, intent_name)
    log_outbound(db, chat_id, response_text, elapsed_ms)

    # Send response back via Telegram (best-effort, don't fail the webhook)
    try:
        tg_send_message(db, response_text, chat_id=chat_id, parse_mode="Markdown")
    except Exception:
        logger.exception("tg_send_response_failed", chat_id=chat_id[:6] + "***")

    logger.info(
        "tg_webhook_processed",
        chat_id=chat_id[:6] + "***",
        intent=intent_name,
        latency_ms=elapsed_ms,
    )

    return TelegramWebhookResponse(ok=True)
