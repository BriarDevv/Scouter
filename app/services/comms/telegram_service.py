"""Telegram service — Bot API integration for alerts and Hermes agent messaging.

Uses the Telegram Bot API (https://core.telegram.org/bots/api).
Secrets (bot_token) are write-only and never exposed in API responses.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_safe
from app.core.logging import get_logger
from app.models.telegram_credentials import TelegramCredentials

logger = get_logger(__name__)

_SEND_TIMEOUT = 15
_API_BASE = "https://api.telegram.org/bot{token}"


def _get_or_create_credentials(db: Session) -> TelegramCredentials:
    row = db.get(TelegramCredentials, 1)
    if not row:
        row = TelegramCredentials(id=1)
        db.add(row)
        db.flush()
        db.refresh(row)
    return row


def get_credentials(db: Session) -> TelegramCredentials:
    return _get_or_create_credentials(db)


_ALLOWED_FIELDS = {
    "bot_username",
    "bot_token",
    "chat_id",
    "webhook_url",
    "webhook_secret",
}
_SECRET_FIELDS = {"bot_token", "webhook_secret"}


def update_credentials(db: Session, updates: dict) -> TelegramCredentials:
    from app.core.crypto import encrypt_if_needed

    row = _get_or_create_credentials(db)
    for key, value in updates.items():
        if key in _ALLOWED_FIELDS:
            if key in _SECRET_FIELDS and value:
                value = encrypt_if_needed(value)
            setattr(row, key, value)
    db.flush()
    db.refresh(row)
    return row


def to_response_dict(row: TelegramCredentials) -> dict:
    """Return credentials with secrets masked."""
    return {
        "bot_username": row.bot_username,
        "bot_token_set": bool(row.bot_token),
        "chat_id": row.chat_id,
        "webhook_url": row.webhook_url,
        "webhook_secret_set": bool(row.webhook_secret),
        "last_test_at": row.last_test_at,
        "last_test_ok": row.last_test_ok,
        "last_test_error": row.last_test_error,
        "updated_at": row.updated_at,
    }


def _call_telegram(token: str, method: str, payload: dict | None = None) -> dict:
    """Call a Telegram Bot API method."""
    url = f"{_API_BASE.format(token=token)}/{method}"
    with httpx.Client(timeout=_SEND_TIMEOUT) as client:
        if payload:
            resp = client.post(url, json=payload)
        else:
            resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def send_message(
    db: Session,
    text: str,
    *,
    chat_id: str | None = None,
    parse_mode: str = "HTML",
) -> bool:
    """Send a Telegram message using configured credentials."""
    creds = _get_or_create_credentials(db)
    token = decrypt_safe(creds.bot_token)
    if not token:
        logger.debug("telegram_send_skipped_no_token")
        return False

    target_chat = chat_id or creds.chat_id
    if not target_chat:
        logger.debug("telegram_send_skipped_no_chat_id")
        return False

    if getattr(settings, "TELEGRAM_DRY_RUN", False):
        logger.info("telegram_dry_run", message=text[:100])
        return True

    try:
        result = _call_telegram(
            token,
            "sendMessage",
            {
                "chat_id": target_chat,
                "text": text,
                "parse_mode": parse_mode,
            },
        )
        if result.get("ok"):
            logger.info("telegram_sent", chat_id=target_chat[:6] + "***")
            return True
        logger.warning("telegram_send_failed", result=result)
        return False
    except httpx.TimeoutException:
        logger.error("telegram_timeout")
        return False
    except Exception as exc:
        logger.error("telegram_error", error=str(exc))
        return False


def send_alert(
    db: Session,
    *,
    title: str,
    message: str,
    severity: str,
) -> bool:
    """Send a Telegram alert using configured credentials."""
    sev_emoji = {
        "critical": "\u26a0\ufe0f",
        "high": "\U0001f534",
        "warning": "\U0001f7e1",
        "info": "\u2139\ufe0f",
    }
    emoji = sev_emoji.get(severity, "\u2139\ufe0f")
    text = f"{emoji} <b>Scouter — {title}</b>\n\n{message}\n\nSeveridad: {severity.upper()}"
    return send_message(db, text)


def test_telegram(db: Session) -> dict:
    """Test Telegram Bot connectivity using configured credentials."""
    creds = _get_or_create_credentials(db)
    token = decrypt_safe(creds.bot_token)
    if not token:
        result = {"ok": False, "error": "No hay bot token configurado.", "bot_username": None}
        creds.last_test_at = datetime.now(timezone.utc)
        creds.last_test_ok = False
        creds.last_test_error = result["error"]
        db.flush()
        return result

    try:
        # Verify bot token with getMe
        data = _call_telegram(token, "getMe")
        if not data.get("ok"):
            raise ValueError("getMe returned ok=false")

        bot_info = data.get("result", {})
        bot_username = bot_info.get("username")

        # Update bot_username if we got it
        if bot_username and bot_username != creds.bot_username:
            creds.bot_username = bot_username

        # If chat_id is set, try sending a test message
        if creds.chat_id:
            send_ok = send_message(
                db, "✅ Scouter Telegram test — canal configurado correctamente."
            )
            if not send_ok:
                result = {
                    "ok": False,
                    "error": "Bot verificado pero no se pudo enviar mensaje. Verificá el chat_id.",
                    "bot_username": bot_username,
                }
                creds.last_test_at = datetime.now(timezone.utc)
                creds.last_test_ok = False
                creds.last_test_error = result["error"]
                db.flush()
                return result

        result = {"ok": True, "error": None, "bot_username": bot_username}
        creds.last_test_at = datetime.now(timezone.utc)
        creds.last_test_ok = True
        creds.last_test_error = None
        db.flush()
        return result

    except Exception as exc:
        error_msg = str(exc)
        if "401" in error_msg:
            error_msg = "Token inválido o bot desactivado."
        result = {"ok": False, "error": error_msg, "bot_username": None}
        creds.last_test_at = datetime.now(timezone.utc)
        creds.last_test_ok = False
        creds.last_test_error = error_msg
        db.flush()
        return result
