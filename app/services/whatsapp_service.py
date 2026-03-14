"""WhatsApp service — provider abstraction for sending alerts.

Etapa 1: CallMeBot (free, HTTP GET, no complex auth).
Provider interface designed for Twilio/Meta Business API in Etapa 2+.
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from urllib.parse import quote_plus

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.whatsapp_credentials import WhatsAppCredentials

logger = get_logger(__name__)

_SEND_TIMEOUT = 15


class WhatsAppProvider(abc.ABC):
    """Abstract WhatsApp provider — implement for each API."""

    @abc.abstractmethod
    def send_message(self, phone: str, message: str, api_key: str) -> bool:
        """Send a message. Returns True on success."""

    @abc.abstractmethod
    def test_connection(self, phone: str, api_key: str) -> dict:
        """Test connectivity. Returns {ok: bool, error: str|None}."""


class CallMeBotProvider(WhatsAppProvider):
    """CallMeBot free WhatsApp API — https://www.callmebot.com/blog/free-api-whatsapp-messages/"""

    BASE_URL = "https://api.callmebot.com/whatsapp.php"

    def send_message(self, phone: str, message: str, api_key: str) -> bool:
        url = f"{self.BASE_URL}?phone={quote_plus(phone)}&text={quote_plus(message)}&apikey={quote_plus(api_key)}"
        try:
            with httpx.Client(timeout=_SEND_TIMEOUT) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    logger.info("whatsapp_sent", provider="callmebot", phone=phone[:6] + "***")
                    return True
                logger.warning(
                    "whatsapp_send_non_200",
                    provider="callmebot",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return False
        except httpx.TimeoutException:
            logger.error("whatsapp_timeout", provider="callmebot")
            return False
        except Exception as exc:
            logger.error("whatsapp_error", provider="callmebot", error=str(exc))
            return False

    def test_connection(self, phone: str, api_key: str) -> dict:
        test_msg = "ClawScout WhatsApp test - canal configurado correctamente."
        ok = self.send_message(phone, test_msg, api_key)
        return {"ok": ok, "error": None if ok else "No se pudo enviar el mensaje de prueba."}


_PROVIDERS: dict[str, type[WhatsAppProvider]] = {
    "callmebot": CallMeBotProvider,
}


def _get_provider(name: str) -> WhatsAppProvider:
    cls = _PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"WhatsApp provider desconocido: {name}")
    return cls()


def _get_or_create_credentials(db: Session) -> WhatsAppCredentials:
    row = db.get(WhatsAppCredentials, 1)
    if not row:
        row = WhatsAppCredentials(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_credentials(db: Session) -> WhatsAppCredentials:
    return _get_or_create_credentials(db)


def update_credentials(db: Session, updates: dict) -> WhatsAppCredentials:
    row = _get_or_create_credentials(db)
    for key, value in updates.items():
        if hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def to_response_dict(row: WhatsAppCredentials) -> dict:
    """Return credentials with secrets masked."""
    return {
        "provider": row.provider,
        "phone_number": row.phone_number,
        "api_key_set": bool(row.api_key),
        "webhook_url": row.webhook_url,
        "last_test_at": row.last_test_at,
        "last_test_ok": row.last_test_ok,
        "last_test_error": row.last_test_error,
        "updated_at": row.updated_at,
    }


def send_alert(
    db: Session,
    *,
    title: str,
    message: str,
    severity: str,
) -> bool:
    """Send a WhatsApp alert using configured credentials."""
    creds = _get_or_create_credentials(db)
    if not creds.phone_number or not creds.api_key:
        logger.debug("whatsapp_alert_skipped_no_credentials")
        return False

    sev_emoji = {"critical": "\u26a0\ufe0f", "high": "\U0001f534", "warning": "\U0001f7e1", "info": "\u2139\ufe0f"}
    emoji = sev_emoji.get(severity, "\u2139\ufe0f")
    text = f"{emoji} *ClawScout — {title}*\n\n{message}\n\nSeveridad: {severity.upper()}"

    provider = _get_provider(creds.provider)
    return provider.send_message(creds.phone_number, text, creds.api_key)


def test_whatsapp(db: Session) -> dict:
    """Test WhatsApp connectivity using configured credentials."""
    creds = _get_or_create_credentials(db)
    if not creds.phone_number:
        result = {"ok": False, "error": "No hay numero de WhatsApp configurado.", "provider": creds.provider}
        creds.last_test_at = datetime.now(timezone.utc)
        creds.last_test_ok = False
        creds.last_test_error = result["error"]
        db.commit()
        return result
    if not creds.api_key:
        result = {"ok": False, "error": "No hay API key configurada.", "provider": creds.provider}
        creds.last_test_at = datetime.now(timezone.utc)
        creds.last_test_ok = False
        creds.last_test_error = result["error"]
        db.commit()
        return result

    provider = _get_provider(creds.provider)
    result = provider.test_connection(creds.phone_number, creds.api_key)
    result["provider"] = creds.provider

    creds.last_test_at = datetime.now(timezone.utc)
    creds.last_test_ok = result["ok"]
    creds.last_test_error = result.get("error")
    db.commit()
    return result
