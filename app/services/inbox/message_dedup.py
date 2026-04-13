"""Inbound message deduplication logic."""

from __future__ import annotations

import hashlib

from app.mail.inbound_provider import InboundMailMessage
from app.services.inbox.mail_helpers import normalize_email, normalize_message_id, normalize_subject


def build_dedupe_key(payload: InboundMailMessage) -> str:
    provider = payload.provider.lower()
    mailbox = payload.provider_mailbox.lower()
    if payload.provider_message_id:
        return f"{provider}:{mailbox}:provider:{payload.provider_message_id}"

    message_id = normalize_message_id(payload.message_id)
    if message_id:
        return f"{provider}:{mailbox}:message:{message_id}"

    digest_source = "|".join(
        [
            provider,
            mailbox,
            normalize_email(payload.from_email) or "",
            normalize_subject(payload.subject) or "",
            payload.received_at.isoformat() if payload.received_at else "",
            (payload.body_snippet or payload.body_text or "")[:160],
        ]
    )
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return f"{provider}:{mailbox}:fallback:{digest}"
