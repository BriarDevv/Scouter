"""Inbox domain — inbound mail, reply classification, drafting, sending."""

from app.services.inbox.inbound_mail_service import get_inbound_sync_status, sync_inbound_messages
from app.services.inbox.reply_classification_service import classify_inbound_message
from app.services.inbox.reply_draft_review_service import review_reply_assistant_draft_with_reviewer
from app.services.inbox.reply_response_service import generate_reply_assistant_draft
from app.services.inbox.reply_send_service import (
    attach_reply_send_metadata,
    send_reply_assistant_draft,
)

__all__ = [
    "sync_inbound_messages",
    "get_inbound_sync_status",
    "classify_inbound_message",
    "generate_reply_assistant_draft",
    "review_reply_assistant_draft_with_reviewer",
    "send_reply_assistant_draft",
    "attach_reply_send_metadata",
]
