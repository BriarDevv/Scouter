"""Tests for WhatsApp controlled actions (Etapa 3)."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

# Ensure test environment overrides before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ["WHATSAPP_WEBHOOK_SECRET"] = "test-secret-123"

from app.models.lead import Lead, LeadStatus
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.settings import OperationalSettings
from app.services.whatsapp_actions import (
    _reset_rate_limits,
    check_action_rate_limit,
    execute_approve_draft,
    execute_mark_read_all,
    execute_reject_draft,
    execute_resolve_notification,
    validate_uuid,
)
from app.services.whatsapp_confirmation import (
    PendingAction,
    _reset_state,
    cancel_pending,
    confirm_pending,
    create_pending,
    has_pending,
    is_locked,
    record_failed_confirmation,
)
from app.services.whatsapp_conversation import (
    Intent,
    _detect_intent,
    _rate_window,
    handle_inbound_message,
)


# -- Helpers --


def _clear_all_state():
    """Clear all in-memory state for a clean test."""
    _rate_window.clear()
    _reset_state()
    _reset_rate_limits()


def _create_lead(db, name="Test Biz", score=75.0, status=LeadStatus.SCORED, **kw):
    lead = Lead(
        id=kw.get("id", uuid.uuid4()),
        business_name=name,
        score=score,
        status=status,
        city=kw.get("city", "Buenos Aires"),
        website_url=kw.get("website_url", "https://test.com"),
        email=kw.get("email", "test@test.com"),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _create_notification(
    db,
    title="Alert",
    message="Something happened",
    severity=NotificationSeverity.HIGH,
    status=NotificationStatus.UNREAD,
):
    n = Notification(
        type="test_alert",
        category=NotificationCategory.BUSINESS,
        severity=severity,
        title=title,
        message=message,
        status=status,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def _create_draft(db, lead, subject="Propuesta Web", status=DraftStatus.PENDING_REVIEW):
    d = OutreachDraft(
        lead_id=lead.id,
        subject=subject,
        body="Hola, le escribo para...",
        status=status,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _enable_actions(db):
    """Enable both conversational and actions in settings."""
    row = db.get(OperationalSettings, 1)
    if not row:
        row = OperationalSettings(
            id=1,
            whatsapp_conversational_enabled=True,
            whatsapp_actions_enabled=True,
        )
        db.add(row)
    else:
        row.whatsapp_conversational_enabled = True
        row.whatsapp_actions_enabled = True
    db.commit()
    return row


def _disable_actions(db):
    """Disable actions in settings."""
    row = db.get(OperationalSettings, 1)
    if not row:
        row = OperationalSettings(
            id=1,
            whatsapp_conversational_enabled=True,
            whatsapp_actions_enabled=False,
        )
        db.add(row)
    else:
        row.whatsapp_actions_enabled = False
    db.commit()
    return row


# -- Intent detection tests for action intents --


class TestActionIntentDetection:
    def test_resolve_notification(self):
        intent, arg = _detect_intent("resolver #abc123")
        assert intent == Intent.RESOLVE_NOTIFICATION
        assert arg == "abc123"

    def test_resolve_english(self):
        intent, arg = _detect_intent("resolve #xyz")
        assert intent == Intent.RESOLVE_NOTIFICATION
        assert arg == "xyz"

    def test_mark_read_leido(self):
        assert _detect_intent("leido") == (Intent.MARK_READ_NOTIFICATIONS, None)

    def test_mark_read_leidos(self):
        assert _detect_intent("leidos") == (Intent.MARK_READ_NOTIFICATIONS, None)

    def test_mark_read_english(self):
        assert _detect_intent("mark read") == (Intent.MARK_READ_NOTIFICATIONS, None)

    def test_approve_draft(self):
        intent, arg = _detect_intent("aprobar #draft123")
        assert intent == Intent.APPROVE_DRAFT
        assert arg == "draft123"

    def test_approve_english(self):
        intent, arg = _detect_intent("approve #draft456")
        assert intent == Intent.APPROVE_DRAFT
        assert arg == "draft456"

    def test_reject_draft(self):
        intent, arg = _detect_intent("rechazar #draft789")
        assert intent == Intent.REJECT_DRAFT
        assert arg == "draft789"

    def test_reject_english(self):
        intent, arg = _detect_intent("reject #id")
        assert intent == Intent.REJECT_DRAFT
        assert arg == "id"

    def test_generate_draft_generar(self):
        intent, arg = _detect_intent("generar draft Panaderia")
        assert intent == Intent.GENERATE_DRAFT
        assert arg == "Panaderia"

    def test_generate_draft_para(self):
        intent, arg = _detect_intent("draft para Mi Negocio")
        assert intent == Intent.GENERATE_DRAFT
        assert arg == "Mi Negocio"


# -- Confirmation system tests --


class TestConfirmationFlow:
    def setup_method(self):
        _clear_all_state()

    def test_create_pending(self):
        msg = create_pending("+5491100000000", "approve_draft", {"draft_id": "abc"}, "Aprobar borrador")
        assert "Confirmar" in msg
        assert "Aprobar borrador" in msg
        assert "SI" in msg
        assert has_pending("+5491100000000")

    def test_confirm_pending(self):
        create_pending("+5491100000000", "approve_draft", {"draft_id": "abc"}, "Aprobar borrador")
        action = confirm_pending("+5491100000000")
        assert action is not None
        assert action.intent == "approve_draft"
        assert action.params == {"draft_id": "abc"}
        assert not has_pending("+5491100000000")

    def test_cancel_pending(self):
        create_pending("+5491100000000", "approve_draft", {"draft_id": "abc"}, "Aprobar borrador")
        result = cancel_pending("+5491100000000")
        assert result is True
        assert not has_pending("+5491100000000")

    def test_cancel_no_pending(self):
        result = cancel_pending("+5491100000000")
        assert result is False

    def test_confirm_no_pending(self):
        action = confirm_pending("+5491100000000")
        assert action is None

    def test_one_pending_per_phone(self):
        create_pending("+5491100000000", "approve_draft", {"draft_id": "first"}, "Primer borrador")
        create_pending("+5491100000000", "reject_draft", {"draft_id": "second"}, "Segundo borrador")
        action = confirm_pending("+5491100000000")
        assert action is not None
        assert action.params["draft_id"] == "second"  # Last one wins


class TestConfirmationExpiry:
    def setup_method(self):
        _clear_all_state()

    def test_confirmation_expiry(self):
        create_pending("+5491100000000", "approve_draft", {"draft_id": "abc"}, "Aprobar borrador")
        assert has_pending("+5491100000000")

        # Mock the pending action to have been created 6 minutes ago
        from app.services.whatsapp_confirmation import _pending
        action = _pending["+5491100000000"]
        action.created_at = datetime.now(timezone.utc) - timedelta(minutes=6)

        # After cleanup, should be expired
        assert not has_pending("+5491100000000")


class TestConfirmationFlowApproveDraft:
    """End-to-end: create pending -> confirm -> executed."""

    def setup_method(self):
        _clear_all_state()

    def test_confirmation_flow_approve_draft(self, db):
        _enable_actions(db)
        lead = _create_lead(db, "Pizzeria Roma")
        draft = _create_draft(db, lead, "Propuesta web para Pizzeria Roma")
        phone = "+5491100020000"

        # Step 1: User sends approve command
        result = handle_inbound_message(db, phone, "aprobar #" + str(draft.id))
        assert "Confirmar" in result
        assert "SI" in result

        # Step 2: User confirms
        result = handle_inbound_message(db, phone, "si")
        assert "aprobado" in result.lower() or "Borrador aprobado" in result

        # Verify draft was actually approved
        db.refresh(draft)
        assert draft.status == DraftStatus.APPROVED

    def test_confirmation_flow_cancel(self, db):
        _enable_actions(db)
        lead = _create_lead(db, "Libreria Atenea")
        draft = _create_draft(db, lead, "Propuesta para Libreria")
        phone = "+5491100020001"

        # Step 1: User sends approve command
        result = handle_inbound_message(db, phone, "aprobar #" + str(draft.id))
        assert "Confirmar" in result

        # Step 2: User cancels
        result = handle_inbound_message(db, phone, "no")
        assert "cancelada" in result.lower()

        # Verify draft was NOT changed
        db.refresh(draft)
        assert draft.status == DraftStatus.PENDING_REVIEW


class TestResolveNotificationAction:
    def setup_method(self):
        _clear_all_state()

    def test_resolve_notification_action(self, db):
        _enable_actions(db)
        notif = _create_notification(db, title="Test Alert", message="Something")
        phone = "+5491100030000"

        # Step 1: Send resolve command
        result = handle_inbound_message(db, phone, "resolver #" + str(notif.id))
        assert "Confirmar" in result

        # Step 2: Confirm
        result = handle_inbound_message(db, phone, "si")
        assert "resuelta" in result.lower()

        # Verify notification was resolved
        db.refresh(notif)
        assert notif.status == NotificationStatus.RESOLVED


class TestMarkReadAction:
    def setup_method(self):
        _clear_all_state()

    def test_mark_read_action(self, db):
        _enable_actions(db)
        _create_notification(db, title="Alert 1", message="Msg 1")
        _create_notification(db, title="Alert 2", message="Msg 2")
        phone = "+5491100040000"

        # Step 1: Send mark read
        result = handle_inbound_message(db, phone, "leido")
        assert "Confirmar" in result

        # Step 2: Confirm
        result = handle_inbound_message(db, phone, "si")
        assert "marcaron" in result.lower()
        assert "2" in result  # 2 notifications marked


class TestRejectDraftAction:
    def setup_method(self):
        _clear_all_state()

    def test_reject_draft_action(self, db):
        _enable_actions(db)
        lead = _create_lead(db, "Taller Mecanico")
        draft = _create_draft(db, lead, "Propuesta web")
        phone = "+5491100050000"

        # Step 1: Send reject command
        result = handle_inbound_message(db, phone, "rechazar #" + str(draft.id))
        assert "Confirmar" in result

        # Step 2: Confirm
        result = handle_inbound_message(db, phone, "si")
        assert "rechazado" in result.lower()

        # Verify draft was rejected
        db.refresh(draft)
        assert draft.status == DraftStatus.REJECTED


class TestActionsDisabled:
    def setup_method(self):
        _clear_all_state()

    def test_actions_disabled_returns_error(self, db):
        _disable_actions(db)
        phone = "+5491100060000"

        result = handle_inbound_message(db, phone, "leido")
        assert "no estan habilitadas" in result.lower()


class TestActionRateLimiting:
    def setup_method(self):
        _clear_all_state()

    def test_action_rate_limiting(self, db):
        _enable_actions(db)
        phone = "+5491100070000"

        # Exhaust rate limit (10 actions per hour)
        for i in range(10):
            # Each call to an action intent checks rate limit
            check_action_rate_limit(phone)

        # Next action should be rate limited
        result = handle_inbound_message(db, phone, "leido")
        assert "limite de acciones" in result.lower()


class TestInvalidUuidRejected:
    def setup_method(self):
        _clear_all_state()

    def test_invalid_uuid_rejected(self, db):
        _enable_actions(db)
        phone = "+5491100080000"

        # Send approve with invalid UUID
        result = handle_inbound_message(db, phone, "aprobar #not-a-uuid")
        assert "Confirmar" in result

        # Confirm to trigger execution with bad UUID
        result = handle_inbound_message(db, phone, "si")
        assert "invalido" in result.lower()

    def test_validate_uuid_valid(self):
        uid = uuid.uuid4()
        assert validate_uuid(str(uid)) == uid

    def test_validate_uuid_invalid(self):
        assert validate_uuid("not-a-uuid") is None
        assert validate_uuid("") is None


class TestPhoneLockout:
    def setup_method(self):
        _clear_all_state()

    def test_lockout_after_failed_confirmations(self, db):
        _enable_actions(db)
        phone = "+5491100090000"

        # Create a pending action
        result = handle_inbound_message(db, phone, "leido")
        assert "Confirmar" in result

        # Send 3 wrong responses (not SI or NO)
        handle_inbound_message(db, phone, "maybe")
        # Need to recreate pending since the first wrong answer doesn't cancel it
        # but the pending is still there

        # Create pending again (the previous one might still be there)
        result = handle_inbound_message(db, phone, "quizas")
        # Third wrong attempt should trigger lockout
        result = handle_inbound_message(db, phone, "tal vez")
        assert "bloqueado" in result.lower()

        # Now all messages should be blocked
        result = handle_inbound_message(db, phone, "leads")
        assert "bloqueado" in result.lower()


class TestReadOnlyIntentsStillWork:
    """Verify that read-only intents still work without confirmation."""

    def setup_method(self):
        _clear_all_state()

    def test_leads_no_confirmation_needed(self, db):
        _create_lead(db, "Test Lead", score=80.0)
        phone = "+5491100100000"
        result = handle_inbound_message(db, phone, "leads")
        assert "Test Lead" in result
        # No confirmation prompt
        assert "Confirmar" not in result

    def test_stats_no_confirmation_needed(self, db):
        phone = "+5491100100001"
        result = handle_inbound_message(db, phone, "stats")
        assert "Resumen" in result
        assert "Confirmar" not in result


class TestHelpIncludesActionCommands:
    def setup_method(self):
        _clear_all_state()

    def test_help_shows_action_commands(self, db):
        phone = "+5491100110000"
        result = handle_inbound_message(db, phone, "ayuda")
        assert "resolver" in result.lower()
        assert "aprobar" in result.lower()
        assert "rechazar" in result.lower()
        assert "generar draft" in result.lower()
        assert "leido" in result.lower()
