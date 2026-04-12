"""Kapso WhatsApp Cloud API client for outreach delivery.

Uses Kapso as a proxy to the WhatsApp Business Cloud API.
Endpoint: POST {base_url}/v24.0/{phone_number_id}/messages

Two main operations:
- send_text_message: Free-form text (only within 24h conversation window)
- send_template_message: Meta-approved template (opens new conversation)
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_API_VERSION = "v24.0"


class KapsoError(Exception):
    """Error communicating with Kapso WhatsApp API."""


def _messages_url() -> str:
    """Build the messages endpoint URL."""
    if not settings.KAPSO_PHONE_NUMBER_ID:
        raise KapsoError("KAPSO_PHONE_NUMBER_ID not configured")
    base = settings.KAPSO_BASE_URL.rstrip("/")
    return f"{base}/{_API_VERSION}/{settings.KAPSO_PHONE_NUMBER_ID}/messages"


def _get_api_key() -> str:
    """Return the effective Kapso API key (DB > env).

    Falls back to env when no DB session is available (e.g. Celery workers).
    """
    try:
        from app.db.session import SessionLocal
        from app.services.deploy_config_service import get_effective_kapso_api_key

        with SessionLocal() as db:
            key = get_effective_kapso_api_key(db)
            if key:
                return key
    except Exception:
        logger.debug("kapso_db_key_lookup_failed", exc_info=True)
    if settings.KAPSO_API_KEY:
        return settings.KAPSO_API_KEY
    raise KapsoError("KAPSO_API_KEY not configured")


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": _get_api_key(),
        "Content-Type": "application/json",
    }


def _post(payload: dict) -> dict:
    """Send a message via Kapso and return the parsed response."""
    url = _messages_url()
    headers = _headers()

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            messages = data.get("messages", [])
            message_id = messages[0]["id"] if messages else None

            logger.info(
                "kapso_send_success",
                message_id=message_id,
                to=payload.get("to", "")[:6] + "***",
            )
            return {
                "message_id": message_id,
                "contacts": data.get("contacts", []),
            }
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        logger.error("kapso_http_error", status=exc.response.status_code, body=body)
        raise KapsoError(f"Kapso API {exc.response.status_code}: {body}") from exc
    except httpx.ConnectError as exc:
        logger.error("kapso_connect_error")
        raise KapsoError("No se pudo conectar a Kapso") from exc


def send_text_message(phone: str, message: str) -> dict:
    """Send a free-form text message (only works within 24h conversation window).

    Args:
        phone: Recipient in international format without + (e.g. 5491158399708)
        message: Text body (max ~4096 chars)

    Returns:
        Dict with message_id.
    """
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone.lstrip("+"),
        "type": "text",
        "text": {"body": message},
    }
    logger.info("kapso_send_text", phone=phone[:6] + "***", body_len=len(message))
    return _post(payload)


def send_template_message(
    phone: str,
    template_name: str,
    language: str = "es_AR",
    parameters: list[dict] | None = None,
) -> dict:
    """Send a Meta-approved template message (opens new conversation).

    Args:
        phone: Recipient in international format without + (e.g. 5491158399708)
        template_name: Name of the approved template (e.g. apertura_general)
        language: Template language code (default es_AR)
        parameters: List of component parameters, e.g.:
            [{"type": "body", "parameters": [{"type": "text", "text": "Juan"}]}]

    Returns:
        Dict with message_id.
    """
    template: dict = {
        "name": template_name,
        "language": {"code": language},
    }
    if parameters:
        template["components"] = parameters

    payload = {
        "messaging_product": "whatsapp",
        "to": phone.lstrip("+"),
        "type": "template",
        "template": template,
    }
    logger.info(
        "kapso_send_template",
        phone=phone[:6] + "***",
        template=template_name,
        lang=language,
    )
    return _post(payload)


# Backward compatibility alias
send_whatsapp_message = send_text_message
