"""Notifications domain — creation, emission, channel dispatch."""

from app.services.notifications.notification_service import (
    create_notification,
    bulk_update_notifications,
    update_notification_status,
)
from app.services.notifications.notification_emitter import (
    on_brief_generated,
    on_high_score_lead,
    on_reply_classified,
    on_send_failed,
    on_sync_failed,
    on_draft_needs_review,
    on_security_event,
    on_research_completed,
)

__all__ = [
    "create_notification",
    "bulk_update_notifications",
    "update_notification_status",
    "on_brief_generated",
    "on_high_score_lead",
    "on_reply_classified",
    "on_send_failed",
    "on_sync_failed",
    "on_draft_needs_review",
    "on_security_event",
    "on_research_completed",
]
