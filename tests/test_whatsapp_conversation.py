"""Tests for WhatsApp conversational interface (Etapa 2)."""

import os
import uuid

import pytest

# Ensure test environment overrides before importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ["WHATSAPP_WEBHOOK_SECRET"] = "test-secret-123"

from app.models.lead import Lead, LeadStatus
from app.models.notification import Notification, NotificationCategory, NotificationSeverity, NotificationStatus
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.settings import OperationalSettings
from app.models.whatsapp_audit import WhatsAppAuditLog
from app.services.whatsapp_conversation import (
    Intent,
    _check_rate_limit,
    _detect_intent,
    _help_message,
    _rate_window,
    _sanitize,
    handle_inbound_message,
)


# ── Helpers ────────────────────────────────────────────────────────────────


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


def _create_notification(db, title="Alert", message="Something happened", severity=NotificationSeverity.HIGH):
    n = Notification(
        type="test_alert",
        category=NotificationCategory.BUSINESS,
        severity=severity,
        title=title,
        message=message,
        status=NotificationStatus.UNREAD,
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


def _enable_conversational(db):
    row = db.get(OperationalSettings, 1)
    if not row:
        row = OperationalSettings(id=1, whatsapp_conversational_enabled=True)
        db.add(row)
    else:
        row.whatsapp_conversational_enabled = True
    db.commit()
    return row


def _clear_rate_limits():
    _rate_window.clear()


# ── Intent detection tests ─────────────────────────────────────────────────


class TestIntentDetection:
    def test_help_command(self):
        assert _detect_intent("ayuda") == (Intent.HELP, None)
        assert _detect_intent("help") == (Intent.HELP, None)
        assert _detect_intent("?") == (Intent.HELP, None)

    def test_leads_command(self):
        assert _detect_intent("leads") == (Intent.QUERY_LEADS, None)
        assert _detect_intent("prospectos") == (Intent.QUERY_LEADS, None)

    def test_lead_detail_command(self):
        intent, arg = _detect_intent("lead Panaderia Don Jose")
        assert intent == Intent.QUERY_LEAD_DETAIL
        assert arg == "Panaderia Don Jose"

    def test_notifications_command(self):
        assert _detect_intent("notificaciones") == (Intent.QUERY_NOTIFICATIONS, None)
        assert _detect_intent("alertas") == (Intent.QUERY_NOTIFICATIONS, None)

    def test_drafts_command(self):
        assert _detect_intent("borradores") == (Intent.QUERY_DRAFTS, None)
        assert _detect_intent("drafts") == (Intent.QUERY_DRAFTS, None)

    def test_stats_command(self):
        assert _detect_intent("stats") == (Intent.QUERY_STATS, None)
        assert _detect_intent("resumen") == (Intent.QUERY_STATS, None)

    def test_unknown_command_returns_help(self):
        intent, _ = _detect_intent("foobar123")
        assert intent == Intent.HELP


# ── Sanitization tests ─────────────────────────────────────────────────────


class TestSanitization:
    def test_strips_html(self):
        result = _sanitize("<b>hello</b> world")
        assert result == "hello world"

    def test_limits_length(self):
        long_msg = "a" * 1000
        result = _sanitize(long_msg)
        assert result is not None
        assert len(result) == 500

    def test_rejects_sql_injection(self):
        assert _sanitize("DROP TABLE leads") is None
        assert _sanitize("1; DELETE FROM leads") is None
        assert _sanitize("x UNION SELECT * FROM users") is None

    def test_rejects_script_injection(self):
        assert _sanitize("<script>alert(1)</script>") is None

    def test_rejects_prompt_injection(self):
        assert _sanitize("ignore previous instructions") is None
        assert _sanitize("system prompt override") is None

    def test_allows_normal_text(self):
        assert _sanitize("leads") == "leads"
        assert _sanitize("  ayuda  ") == "ayuda"


# ── Rate limiting tests ───────────────────────────────────────────────────


class TestRateLimiting:
    def setup_method(self):
        _clear_rate_limits()

    def test_allows_within_limit(self):
        for _ in range(20):
            assert _check_rate_limit("+5491112345678") is True

    def test_blocks_over_limit(self):
        for _ in range(20):
            _check_rate_limit("+5491112345678")
        assert _check_rate_limit("+5491112345678") is False

    def test_different_phones_independent(self):
        for _ in range(20):
            _check_rate_limit("+5491111111111")
        assert _check_rate_limit("+5491111111111") is False
        assert _check_rate_limit("+5491122222222") is True


# ── Query tests (require DB) ──────────────────────────────────────────────


class TestQueryLeads:
    def test_query_leads_empty(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000000", "leads")
        assert "No hay leads con score" in result

    def test_query_leads_with_data(self, db):
        _clear_rate_limits()
        _create_lead(db, "Panaderia Don Jose", score=90.0)
        _create_lead(db, "Libreria Central", score=80.0)
        _create_lead(db, "Taller Mecanico", score=70.0)
        result = handle_inbound_message(db, "+5491100000001", "leads")
        assert "Panaderia Don Jose" in result
        assert "Libreria Central" in result
        assert "Top 5" in result

    def test_query_lead_detail_by_name(self, db):
        _clear_rate_limits()
        _create_lead(db, "Farmacia del Pueblo", score=85.0, city="Rosario", email="farm@test.com")
        result = handle_inbound_message(db, "+5491100000002", "lead Farmacia")
        assert "Farmacia del Pueblo" in result
        assert "Rosario" in result
        assert "farm@test.com" in result

    def test_query_lead_detail_not_found(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000003", "lead NoExiste")
        assert "No se encontro" in result


class TestQueryNotifications:
    def test_query_notifications_empty(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000004", "notificaciones")
        assert "No hay notificaciones" in result

    def test_query_notifications_with_data(self, db):
        _clear_rate_limits()
        _create_notification(db, title="Nuevo lead alto", message="Lead con score 95 detectado")
        _create_notification(db, title="Error de crawling", message="Timeout en google.com")
        result = handle_inbound_message(db, "+5491100000005", "notificaciones")
        assert "Nuevo lead alto" in result
        assert "Error de crawling" in result


class TestQueryDrafts:
    def test_query_drafts_empty(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000006", "borradores")
        assert "No hay borradores" in result

    def test_query_drafts_with_data(self, db):
        _clear_rate_limits()
        lead = _create_lead(db, "Pizzeria Napoli")
        _create_draft(db, lead, subject="Propuesta de sitio web")
        result = handle_inbound_message(db, "+5491100000007", "borradores")
        assert "Propuesta de sitio web" in result
        assert "Pizzeria Napoli" in result


class TestQueryStats:
    def test_query_stats_empty(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000008", "stats")
        assert "Total leads: 0" in result

    def test_query_stats_with_data(self, db):
        _clear_rate_limits()
        _create_lead(db, "Lead1", score=80.0, status=LeadStatus.CONTACTED)
        _create_lead(db, "Lead2", score=60.0, status=LeadStatus.REPLIED)
        _create_lead(db, "Lead3", score=None, status=LeadStatus.NEW)
        result = handle_inbound_message(db, "+5491100000009", "stats")
        assert "Total leads: 3" in result
        assert "Con score: 2" in result
        assert "Contactados: 2" in result
        assert "Respondieron: 1" in result


class TestHelpCommand:
    def test_help_returns_commands(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000010", "ayuda")
        assert "Comandos disponibles" in result
        assert "leads" in result
        assert "borradores" in result

    def test_unknown_command_includes_hint(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000011", "xyzabc")
        assert "No entendi" in result
        assert "xyzabc" in result
        assert "Comandos disponibles" in result


class TestRateLimitIntegration:
    def test_rate_limit_returns_message(self, db):
        _clear_rate_limits()
        phone = "+5491100099999"
        for _ in range(20):
            handle_inbound_message(db, phone, "leads")
        result = handle_inbound_message(db, phone, "leads")
        assert "limite de mensajes" in result


class TestSanitizationIntegration:
    def test_sql_injection_rejected(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000012", "DROP TABLE leads")
        assert "rechazado" in result

    def test_html_stripped(self, db):
        _clear_rate_limits()
        result = handle_inbound_message(db, "+5491100000013", "<b>ayuda</b>")
        assert "Comandos disponibles" in result


# ── Webhook API tests ──────────────────────────────────────────────────────


class TestWebhookAPI:
    def test_webhook_verify(self, client):
        resp = client.get("/api/v1/whatsapp/webhook", params={"hub.challenge": "abc123"})
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "abc123"

    def test_webhook_missing_secret(self, client):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            json={"phone": "+5491100000000", "message": "leads"},
        )
        assert resp.status_code == 403

    def test_webhook_wrong_secret(self, client):
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            json={"phone": "+5491100000000", "message": "leads"},
            headers={"X-Webhook-Secret": "wrong"},
        )
        assert resp.status_code == 403

    def test_webhook_disabled_feature(self, client, db):
        # Ensure conversational is disabled (default)
        row = db.get(OperationalSettings, 1)
        if row:
            row.whatsapp_conversational_enabled = False
            db.commit()
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            json={"phone": "+5491100000000", "message": "leads"},
            headers={"X-Webhook-Secret": "test-secret-123"},
        )
        assert resp.status_code == 403
        assert "no esta habilitada" in resp.json()["detail"]

    def test_webhook_success(self, client, db):
        _clear_rate_limits()
        _enable_conversational(db)
        _create_lead(db, "Test Lead WH", score=88.0)
        resp = client.post(
            "/api/v1/whatsapp/webhook",
            json={"phone": "+5491100000000", "message": "leads"},
            headers={"X-Webhook-Secret": "test-secret-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "Test Lead WH" in data["response"]

        # Verify audit log was created
        audit_entries = db.query(WhatsAppAuditLog).all()
        assert len(audit_entries) >= 2  # inbound + outbound
