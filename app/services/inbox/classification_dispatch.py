"""Dispatch inbound messages for auto-classification when enabled."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.inbound_mail import InboundMessage

logger = get_logger(__name__)


_AUTO_REPLY_DRAFT_LABELS = {
    "interested",
    "asked_for_quote",
    "asked_for_meeting",
    "positive",
}


def dispatch_classification(db: Session, message: InboundMessage) -> None:
    """Auto-classify *message* if operational settings allow it.

    Uses deferred imports to avoid circular dependencies, matching the
    pattern that existed in the original monolith.
    """
    from app.services.settings.operational_settings_service import get_cached_settings

    ops = get_cached_settings(db)
    if not (message and ops.auto_classify_inbound):
        return

    from app.services.inbox.reply_classification_service import classify_inbound_message

    classified = classify_inbound_message(db, message.id)

    # Auto-generate reply draft for actionable labels when auto pipeline is on
    if (
        classified
        and ops.auto_pipeline_enabled
        and classified.classification_label in _AUTO_REPLY_DRAFT_LABELS
    ):
        try:
            from app.services.inbox.reply_response_service import (
                generate_reply_assistant_draft,
            )

            generate_reply_assistant_draft(db, classified.id)
            logger.info(
                "auto_reply_draft_generated",
                inbound_message_id=str(classified.id),
                label=classified.classification_label,
            )
        except Exception as exc:
            logger.warning(
                "auto_reply_draft_generation_failed",
                inbound_message_id=str(classified.id),
                label=classified.classification_label,
                error=str(exc),
            )
