"""Outreach domain — draft generation, mail sending, auto-send, closer."""

from app.services.outreach.auto_send_service import auto_send_draft
from app.services.outreach.closer_service import generate_closer_response
from app.services.outreach.mail_credentials_service import get_effective_imap, get_effective_smtp
from app.services.outreach.mail_service import send_draft
from app.services.outreach.outreach_service import (
    generate_outreach_draft,
    generate_whatsapp_draft,
)

__all__ = [
    "generate_outreach_draft",
    "generate_whatsapp_draft",
    "send_draft",
    "auto_send_draft",
    "generate_closer_response",
    "get_effective_smtp",
    "get_effective_imap",
]
