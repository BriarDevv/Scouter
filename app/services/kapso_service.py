"""Kapso WhatsApp API client for outreach delivery."""

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KapsoError(Exception):
    """Error communicating with Kapso API."""
    pass


def send_whatsapp_message(phone: str, message: str) -> dict:
    """Send a text message via Kapso WhatsApp API.

    Args:
        phone: Recipient phone number (E.164 format preferred)
        message: Text message body

    Returns:
        Dict with message_id and status from Kapso response.

    Raises:
        KapsoError: If API key is missing or request fails.
    """
    if not settings.KAPSO_API_KEY:
        raise KapsoError("KAPSO_API_KEY not configured")

    url = f"{settings.KAPSO_BASE_URL}/whatsapp_messages"
    headers = {
        "X-API-Key": settings.KAPSO_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "message": {
            "phone_number": phone,
            "content": message,
            "message_type": "text",
        },
    }

    logger.info("kapso_send_request", phone=phone[:6] + "***", body_len=len(message))

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            msg_data = data.get("data", {})
            logger.info(
                "kapso_send_success",
                phone=phone[:6] + "***",
                message_id=msg_data.get("id"),
            )
            return {
                "message_id": msg_data.get("id"),
                "status": msg_data.get("status", "sent"),
            }
    except httpx.HTTPStatusError as exc:
        logger.error("kapso_send_http_error", status=exc.response.status_code)
        raise KapsoError(f"Kapso API error: {exc.response.status_code}") from exc
    except httpx.ConnectError as exc:
        logger.error("kapso_send_connect_error")
        raise KapsoError("No se pudo conectar a Kapso") from exc
