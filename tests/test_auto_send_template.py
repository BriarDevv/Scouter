"""Tests for auto_send_service template-first WhatsApp flow."""

from app.models.lead import Lead
from app.models.lead_signal import LeadSignal, SignalType
from app.models.outbound_conversation import ConversationStatus
from app.models.outreach import DraftStatus, OutreachDraft
from app.services.outreach.auto_send_service import auto_send_draft
from app.services.outreach.template_selection import (
    build_template_parameters,
    select_template,
)

# ---------------------------------------------------------------------------
# Template selection
# ---------------------------------------------------------------------------


def test_select_template_instagram():
    t = select_template(["instagram_only"])
    assert t.name == "apertura_instagram"


def test_select_template_no_website():
    t = select_template(["no_website"])
    assert t.name == "apertura_sin_web"


def test_select_template_outdated():
    t = select_template(["outdated_website"])
    assert t.name == "apertura_web_vieja"


def test_select_template_no_ssl():
    t = select_template(["no_ssl"])
    assert t.name == "apertura_web_vieja"


def test_select_template_default():
    t = select_template(["has_website", "has_custom_domain"])
    assert t.name == "apertura_general"


def test_select_template_empty():
    t = select_template([])
    assert t.name == "apertura_general"


def test_select_template_instagram_priority():
    """Instagram takes priority over no_website."""
    t = select_template(["instagram_only", "no_website"])
    assert t.name == "apertura_instagram"


# ---------------------------------------------------------------------------
# Template parameter building
# ---------------------------------------------------------------------------


def test_build_params_with_contact_name():
    t = select_template([])  # apertura_general
    params = build_template_parameters(t, contact_name="Juan", business_name="Cafe Test")
    assert len(params) == 1
    assert params[0]["type"] == "body"
    assert params[0]["parameters"][0]["text"] == "Juan"


def test_build_params_fallback_to_business_name():
    t = select_template(["no_website"])  # apertura_sin_web
    params = build_template_parameters(t, contact_name="", business_name="Cafe Test")
    assert params[0]["parameters"][0]["text"] == "Cafe Test"


# ---------------------------------------------------------------------------
# Auto-send with template flow
# ---------------------------------------------------------------------------


def test_auto_send_whatsapp_sends_template(db, monkeypatch):
    lead = Lead(
        business_name="WA Test Lead",
        city="CABA",
        industry="Cafe",
        phone="+5491155551234",
    )
    db.add(lead)
    db.flush()
    db.add(LeadSignal(lead_id=lead.id, signal_type=SignalType.NO_WEBSITE))
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Test",
        body="Hola, vi tu negocio...",
        status=DraftStatus.APPROVED,
        channel="whatsapp",
    )
    db.add(draft)
    db.commit()

    # Mock Kapso template send
    captured = {}

    def fake_send_template(phone, template_name, language="es_AR", parameters=None):
        captured["phone"] = phone
        captured["template"] = template_name
        captured["params"] = parameters
        return {"message_id": "wamid.TEST123"}

    monkeypatch.setattr(
        "app.services.comms.kapso_service.send_template_message",
        fake_send_template,
    )

    convo = auto_send_draft(db, draft.id)

    assert convo is not None
    assert convo.status == ConversationStatus.SENT
    assert convo.provider_message_id == "wamid.TEST123"
    assert captured["template"] == "apertura_sin_web"
    assert captured["phone"] == "+5491155551234"

    # Check messages_json has template + queued draft
    msgs = convo.messages_json
    assert len(msgs) == 2
    assert msgs[0]["type"] == "template"
    assert msgs[0]["template_name"] == "apertura_sin_web"
    assert msgs[1]["type"] == "queued_draft"
    assert "vi tu negocio" in msgs[1]["content"]


def test_auto_send_skips_unapproved_draft(db):
    lead = Lead(business_name="Skip Lead", city="CABA", industry="Cafe")
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Test",
        body="Test",
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)
    db.commit()

    result = auto_send_draft(db, draft.id)
    assert result is None


def test_auto_send_skips_no_phone(db, monkeypatch):
    lead = Lead(business_name="No Phone Lead", city="CABA", industry="Cafe")
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Test",
        body="Test",
        status=DraftStatus.APPROVED,
        channel="whatsapp",
    )
    db.add(draft)
    db.commit()

    result = auto_send_draft(db, draft.id)
    assert result is None
