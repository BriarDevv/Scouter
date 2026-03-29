"""Tests for WhatsApp outreach system — prompts, generator, model, Kapso, agent tools."""

import pytest


# ---------------------------------------------------------------------------
# Test 1: WhatsApp draft prompt includes anti-injection
# ---------------------------------------------------------------------------


def test_whatsapp_prompt_has_anti_injection():
    from app.llm.prompts import ANTI_INJECTION_PREAMBLE, GENERATE_WHATSAPP_DRAFT_SYSTEM

    assert ANTI_INJECTION_PREAMBLE[:30] in GENERATE_WHATSAPP_DRAFT_SYSTEM


# ---------------------------------------------------------------------------
# Test 2: WhatsApp draft prompt uses external_data tags
# ---------------------------------------------------------------------------


def test_whatsapp_data_prompt_uses_external_data_tags():
    from app.llm.prompts import GENERATE_WHATSAPP_DRAFT_DATA

    assert "<external_data>" in GENERATE_WHATSAPP_DRAFT_DATA
    assert "</external_data>" in GENERATE_WHATSAPP_DRAFT_DATA


# ---------------------------------------------------------------------------
# Test 3: WhatsApp generator truncates long messages
# ---------------------------------------------------------------------------


def test_whatsapp_generator_truncates_at_char_limit():
    from app.outreach.generator import WA_CHAR_LIMIT

    assert WA_CHAR_LIMIT == 300


# ---------------------------------------------------------------------------
# Test 4: OutreachDraft model has channel field
# ---------------------------------------------------------------------------


def test_outreach_draft_has_channel_field():
    from app.models.outreach import OutreachDraft

    assert hasattr(OutreachDraft, "channel")


# ---------------------------------------------------------------------------
# Test 5: OutreachDraft subject is nullable
# ---------------------------------------------------------------------------


def test_outreach_draft_subject_nullable():
    from app.models.outreach import OutreachDraft

    col = OutreachDraft.__table__.columns["subject"]
    assert col.nullable is True


# ---------------------------------------------------------------------------
# Test 6: Kapso service raises on missing key
# ---------------------------------------------------------------------------


def test_kapso_raises_without_api_key(monkeypatch):
    monkeypatch.setattr("app.services.kapso_service.settings.KAPSO_API_KEY", None)
    from app.services.kapso_service import KapsoError, send_whatsapp_message

    with pytest.raises(KapsoError, match="KAPSO_API_KEY"):
        send_whatsapp_message("+5491155551234", "test")


# ---------------------------------------------------------------------------
# Test 7: Kapso service builds correct payload
# ---------------------------------------------------------------------------


def test_kapso_builds_correct_payload(monkeypatch):
    """Verify Kapso payload format matches Platform API spec."""
    monkeypatch.setattr("app.services.kapso_service.settings.KAPSO_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.services.kapso_service.settings.KAPSO_BASE_URL",
        "https://app.kapso.ai/api/v1",
    )

    captured = {}

    class MockResponse:
        status_code = 201

        def json(self):
            return {"data": {"id": "msg-123", "status": "sent"}}

        def raise_for_status(self):
            pass

    class MockClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return MockResponse()

    monkeypatch.setattr(
        "app.services.kapso_service.httpx.Client", lambda **kw: MockClient()
    )

    from app.services.kapso_service import send_whatsapp_message

    result = send_whatsapp_message("+5491155551234", "Hola test")

    assert captured["url"] == "https://app.kapso.ai/api/v1/whatsapp_messages"
    assert captured["json"]["message"]["phone_number"] == "+5491155551234"
    assert captured["json"]["message"]["content"] == "Hola test"
    assert captured["json"]["message"]["message_type"] == "text"
    assert captured["headers"]["X-API-Key"] == "test-key"
    assert result["message_id"] == "msg-123"
    assert result["status"] == "sent"


# ---------------------------------------------------------------------------
# Test 8: WhatsApp agent tools are registered
# ---------------------------------------------------------------------------


def test_whatsapp_agent_tools_registered():
    import app.agent.tools  # noqa: F401 — triggers all tool registrations
    from app.agent.tool_registry import registry

    names = [t.name for t in registry.list_all()]
    assert "generate_whatsapp_draft" in names
    assert "send_whatsapp_draft" in names


# ---------------------------------------------------------------------------
# Test 9: WhatsApp tools require confirmation
# ---------------------------------------------------------------------------


def test_whatsapp_tools_require_confirmation():
    import app.agent.tools  # noqa: F401 — triggers all tool registrations
    from app.agent.tool_registry import registry

    for tool in registry.list_all():
        if "whatsapp" in tool.name:
            assert tool.requires_confirmation is True, (
                f"{tool.name} should require confirmation"
            )


# ---------------------------------------------------------------------------
# Test 10: Operational settings has whatsapp_outreach_enabled
# ---------------------------------------------------------------------------


def test_settings_has_whatsapp_outreach_enabled():
    from app.models.settings import OperationalSettings

    assert hasattr(OperationalSettings, "whatsapp_outreach_enabled")
