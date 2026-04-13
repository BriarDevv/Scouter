"""Dispatch inbound messages for auto-classification when enabled."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.inbound_mail import InboundMessage

logger = get_logger(__name__)


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

    classify_inbound_message(db, message.id)
