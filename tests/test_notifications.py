"""Tests for notification service, emitter, and WhatsApp provider."""

import uuid

import pytest

from app.models.notification import (
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from app.services.notifications.notification_emitter import (
    on_high_score_lead,
    on_reply_classified,
    on_security_event,
    on_send_failed,
    on_sync_failed,
)
from app.services.notifications.notification_service import (
    bulk_update_notifications,
    create_notification,
    get_notification_counts,
    list_notifications,
    update_notification_status,
)

# ---------------------------------------------------------------------------
# Notification service tests
# ---------------------------------------------------------------------------


class TestNotificationService:
    def test_create_notification(self, db):
        notif = create_notification(
            db,
            type="test_event",
            category="business",
            severity="info",
            title="Test Notification",
            message="This is a test.",
        )
        assert notif is not None
        assert notif.type == "test_event"
        assert notif.category == NotificationCategory.BUSINESS
        assert notif.severity == NotificationSeverity.INFO
        assert notif.status == NotificationStatus.UNREAD
        assert notif.channel_state == {"in_app": "delivered"}

    def test_dedup_by_key(self, db):
        n1 = create_notification(
            db,
            type="test",
            category="business",
            severity="info",
            title="A",
            message="A",
            dedup_key="unique_key_1",
        )
        n2 = create_notification(
            db,
            type="test",
            category="business",
            severity="info",
            title="B",
            message="B",
            dedup_key="unique_key_1",
        )
        assert n1 is not None
        assert n2 is None

    def test_rate_limiting(self, db):
        source_id = uuid.uuid4()
        results = []
        for i in range(5):
            n = create_notification(
                db,
                type="rate_test",
                category="system",
                severity="warning",
                title=f"Rate {i}",
                message=f"Rate {i}",
                source_kind="test",
                source_id=source_id,
            )
            results.append(n)

        created = [r for r in results if r is not None]
        assert len(created) == 3  # rate limit is 3 per 15 min window

    def test_list_with_filters(self, db):
        create_notification(
            db, type="a", category="business", severity="high", title="Biz", message="x"
        )
        create_notification(
            db, type="b", category="security", severity="critical", title="Sec", message="y"
        )
        create_notification(
            db, type="c", category="system", severity="info", title="Sys", message="z"
        )

        items, total, unread = list_notifications(db, category="security")
        assert total == 1
        assert items[0].type == "b"

        items_all, total_all, unread_all = list_notifications(db)
        assert total_all == 3
        assert unread_all == 3

    def test_update_status(self, db):
        notif = create_notification(
            db,
            type="status_test",
            category="business",
            severity="info",
            title="Update Me",
            message="test",
        )
        updated = update_notification_status(db, notif.id, "read")
        assert updated.status == NotificationStatus.READ
        assert updated.read_at is not None

        resolved = update_notification_status(db, notif.id, "resolved")
        assert resolved.status == NotificationStatus.RESOLVED
        assert resolved.resolved_at is not None

    def test_bulk_mark_read(self, db):
        for i in range(3):
            create_notification(
                db,
                type="bulk_test",
                category="business",
                severity="info",
                title=f"Bulk {i}",
                message="x",
            )
        affected = bulk_update_notifications(db, action="mark_read", category="business")
        assert affected == 3

    def test_counts(self, db):
        create_notification(
            db, type="a", category="business", severity="high", title="A", message="x"
        )
        create_notification(
            db, type="b", category="security", severity="critical", title="B", message="y"
        )
        create_notification(
            db, type="c", category="system", severity="info", title="C", message="z"
        )

        counts = get_notification_counts(db)
        assert counts["total_unread"] == 3
        assert counts["business"] == 1
        assert counts["security"] == 1
        assert counts["critical"] == 1
        assert counts["high"] == 1


# ---------------------------------------------------------------------------
# Notification emitter tests
# ---------------------------------------------------------------------------


class TestNotificationEmitter:
    def test_reply_interested_emits(self, db):
        msg_id = uuid.uuid4()
        on_reply_classified(
            db,
            message_id=msg_id,
            label="interested",
            business_name="Cafe Test",
            from_email="test@example.com",
            confidence=0.9,
            should_escalate=False,
        )
        items, total, _ = list_notifications(db, type="reply_interested")
        assert total == 1
        assert "Cafe Test" in items[0].title

    def test_quote_request_emits(self, db):
        msg_id = uuid.uuid4()
        on_reply_classified(
            db,
            message_id=msg_id,
            label="asked_for_quote",
            business_name="Shop",
            from_email="shop@example.com",
            confidence=0.85,
            should_escalate=False,
        )
        items, total, _ = list_notifications(db, type="quote_request")
        assert total == 1

    def test_low_value_label_does_not_emit(self, db):
        msg_id = uuid.uuid4()
        on_reply_classified(
            db,
            message_id=msg_id,
            label="not_interested",
            business_name="Meh",
            from_email="meh@example.com",
            confidence=0.9,
            should_escalate=False,
        )
        items, total, _ = list_notifications(db)
        assert total == 0

    def test_escalation_emits_review_required(self, db):
        msg_id = uuid.uuid4()
        on_reply_classified(
            db,
            message_id=msg_id,
            label="neutral",
            business_name="Ambiguous",
            from_email="a@example.com",
            confidence=0.3,
            should_escalate=True,
        )
        items, total, _ = list_notifications(db, type="review_required")
        assert total == 1

    def test_high_score_lead_emits(self, db):
        lead_id = uuid.uuid4()
        on_high_score_lead(db, lead_id=lead_id, business_name="Hot Lead", score=85, threshold=70)
        items, total, _ = list_notifications(db, type="high_score_lead")
        assert total == 1
        assert "Hot Lead" in items[0].title

    def test_high_score_below_threshold_no_emit(self, db):
        lead_id = uuid.uuid4()
        on_high_score_lead(db, lead_id=lead_id, business_name="Cold", score=50, threshold=70)
        items, total, _ = list_notifications(db)
        assert total == 0

    def test_send_failed_emits(self, db):
        delivery_id = uuid.uuid4()
        on_send_failed(db, delivery_id=delivery_id, recipient="test@x.com", error="SMTP timeout")
        items, total, _ = list_notifications(db, type="send_failed")
        assert total == 1
        assert items[0].severity == NotificationSeverity.HIGH

    def test_sync_failed_emits(self, db):
        run_id = uuid.uuid4()
        on_sync_failed(db, sync_run_id=run_id, error="IMAP connection refused")
        items, total, _ = list_notifications(db, type="sync_failed")
        assert total == 1

    def test_security_event_emits(self, db):
        on_security_event(
            db,
            event_type="prompt_injection_detected",
            title="Intento de inyeccion detectado",
            message="Email body contenia instrucciones sospechosas.",
            severity="critical",
        )
        items, total, _ = list_notifications(db, category="security")
        assert total == 1
        assert items[0].severity == NotificationSeverity.CRITICAL


# ---------------------------------------------------------------------------
# WhatsApp provider tests
# ---------------------------------------------------------------------------


class TestWhatsAppProvider:
    def test_callmebot_format(self):
        from app.services.comms.whatsapp_service import CallMeBotProvider

        provider = CallMeBotProvider()
        # Just verify the class instantiates and has the right methods
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "test_connection")

    def test_provider_registry(self):
        from app.services.comms.whatsapp_service import _get_provider

        provider = _get_provider("callmebot")
        assert provider is not None
        with pytest.raises(ValueError):
            _get_provider("nonexistent")
