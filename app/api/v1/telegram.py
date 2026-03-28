"""Telegram webhook — routes inbound messages through the Hermes 3 agent."""

from __future__ import annotations

import os
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agent.channel_router import handle_channel_message
from app.api.deps import get_session
from app.core.logging import get_logger
from app.models.settings import OperationalSettings
from app.services.telegram_audit import log_inbound, log_outbound
from app.services.telegram_service import send_message as tg_send_message

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramWebhookResponse(BaseModel):
    ok: bool


def _get_settings(db: Session) -> OperationalSettings:
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
    """Receive Telegram updates, process via Hermes 3 agent, send response."""
    message_obj = body.get("message") or body.get("edited_message")
    if not message_obj:
        return TelegramWebhookResponse(ok=True)

    text = message_obj.get("text", "")
    chat_id = str(message_obj.get("chat", {}).get("id", ""))
    if not text or not chat_id:
        return TelegramWebhookResponse(ok=True)

    # Validate webhook secret
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
    if not getattr(settings, "telegram_agent_enabled", False):
        logger.info("tg_agent_disabled")
        raise HTTPException(status_code=403, detail="Telegram agent no habilitado.")

    # Process via Hermes 3 agent
    start = time.monotonic()
    response_text = handle_channel_message(
        db=db, channel="telegram", channel_id=chat_id, message=text,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Audit
    log_inbound(db, chat_id, text, "agent")
    log_outbound(db, chat_id, response_text, elapsed_ms)

    # Send response
    try:
        tg_send_message(db, response_text, chat_id=chat_id, parse_mode="Markdown")
    except Exception:
        logger.exception("tg_send_response_failed", chat_id=chat_id[:6] + "***")

    logger.info("tg_webhook_processed", chat_id=chat_id[:6] + "***", latency_ms=elapsed_ms)
    return TelegramWebhookResponse(ok=True)
