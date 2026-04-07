"""Comms domain — WhatsApp, Telegram, Kapso integrations."""

from app.services.comms.kapso_service import send_template_message, send_text_message
from app.services.comms.whatsapp_service import send_message_to_phone, send_alert as whatsapp_send_alert
from app.services.comms.telegram_service import send_alert as telegram_send_alert

__all__ = [
    "send_template_message",
    "send_text_message",
    "send_message_to_phone",
    "whatsapp_send_alert",
    "telegram_send_alert",
]
