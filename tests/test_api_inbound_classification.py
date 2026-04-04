from app.llm.invocation_metadata import LLMInvocationMetadata
from app.llm.types import LLMInvocationStatus
from app.models.inbound_mail import InboundMailClassificationStatus
from app.services.inbox.inbound_mail_service import sync_inbound_messages
from app.services.inbox.reply_classification_service import VALID_REPLY_LABELS

from helpers import create_sent_delivery, message_payload


def _seed_inbound_message(
    db,
    monkeypatch,
    *,
    delivery_message_id: str = "out-xyz",
    suffix: str = "001",
):
    create_sent_delivery(db, provider_message_id=delivery_message_id)
    payload = message_payload(
        provider_message_id=f"imap-classify-{suffix}",
        message_id=f"<reply-classify-{suffix}@example.com>",
        in_reply_to=f"<{delivery_message_id}>",
        body_text="Hola, me interesa avanzar y agendar una reunión.",
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            return [payload]

    monkeypatch.setattr("app.services.inbox.inbound_mail_service.get_inbound_provider", lambda: FakeProvider())
    message = sync_inbound_messages(db, limit=1)
    assert message.new_count == 1
    return payload


def test_classify_inbound_message_success(client, db, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MAIL_INBOUND_ENABLED", True)
    _seed_inbound_message(db, monkeypatch, delivery_message_id="out-xyz", suffix="001")

    def fake_classifier(**kwargs):
        return {
            "label": "asked_for_meeting",
            "summary": "El lead quiere coordinar una reunión.",
            "confidence": 0.91,
            "next_action_suggestion": "Responder proponiendo dos horarios.",
            "should_escalate_reviewer": False,
        }

    monkeypatch.setattr(
        "app.services.inbox.reply_classification_service.llm_classify_inbound_reply",
        fake_classifier,
    )

    message = client.get("/api/v1/mail/inbound/messages").json()[0]
    resp = client.post(f"/api/v1/mail/inbound/messages/{message['id']}/classify")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["classification_status"] == InboundMailClassificationStatus.CLASSIFIED.value
    assert payload["classification_label"] == "asked_for_meeting"
    assert payload["summary"] == "El lead quiere coordinar una reunión."
    assert payload["confidence"] == 0.91
    assert payload["next_action_suggestion"] == "Responder proponiendo dos horarios."
    assert payload["should_escalate_reviewer"] is False
    assert payload["classification_role"] == "executor"
    assert payload["classification_model"] == "qwen3.5:9b"
    assert payload["classified_at"] is not None
    assert payload["classification_error"] is None


def test_classify_inbound_message_failure_persists_error(client, db, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MAIL_INBOUND_ENABLED", True)
    _seed_inbound_message(db, monkeypatch, delivery_message_id="out-xyz", suffix="002")

    def broken_classifier(**kwargs):
        raise RuntimeError("ollama timeout")

    monkeypatch.setattr(
        "app.services.inbox.reply_classification_service.llm_classify_inbound_reply",
        broken_classifier,
    )

    message = client.get("/api/v1/mail/inbound/messages").json()[0]
    resp = client.post(f"/api/v1/mail/inbound/messages/{message['id']}/classify")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["classification_status"] == InboundMailClassificationStatus.FAILED.value
    assert payload["classification_error"] == "ollama timeout"
    assert payload["classification_label"] is None
    assert payload["classification_role"] == "executor"
    assert payload["classification_model"] == "qwen3.5:9b"


def test_classify_inbound_message_uses_actual_invocation_metadata(client, db, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MAIL_INBOUND_ENABLED", True)
    _seed_inbound_message(db, monkeypatch, delivery_message_id="out-xyz", suffix="003")

    def fake_classifier(**kwargs):
        return {
            "label": "interested",
            "summary": "Quiere avanzar.",
            "confidence": 0.8,
            "next_action_suggestion": "Responder con próximos pasos.",
            "should_escalate_reviewer": False,
        }

    monkeypatch.setattr(
        "app.services.inbox.reply_classification_service.llm_classify_inbound_reply",
        fake_classifier,
    )
    monkeypatch.setattr(
        "app.services.inbox.reply_classification_service.peek_last_invocation",
        lambda: LLMInvocationMetadata(
            function_name="classify_inbound_reply",
            prompt_id="inbound_reply.classify",
            prompt_version="v1",
            role="executor",
            status=LLMInvocationStatus.DEGRADED,
            model="qwen3.5:9b-instrumented",
            fallback_used=False,
            degraded=True,
            parse_valid=True,
        ),
    )

    message = client.get("/api/v1/mail/inbound/messages").json()[0]
    resp = client.post(f"/api/v1/mail/inbound/messages/{message['id']}/classify")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["classification_role"] == "executor"
    assert payload["classification_model"] == "qwen3.5:9b-instrumented"


def test_classify_pending_endpoint_and_filter(client, db, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.MAIL_INBOUND_ENABLED", True)
    _seed_inbound_message(db, monkeypatch, delivery_message_id="out-101", suffix="101")
    _seed_inbound_message(db, monkeypatch, delivery_message_id="out-102", suffix="102")

    responses = iter(
        [
            {
                "label": "interested",
                "summary": "Quiere avanzar.",
                "confidence": 0.72,
                "next_action_suggestion": "Responder con próximos pasos.",
                "should_escalate_reviewer": False,
            },
            {
                "label": "needs_human_review",
                "summary": "La respuesta es ambigua y requiere criterio humano.",
                "confidence": 0.31,
                "next_action_suggestion": "Escalar para revisión manual.",
                "should_escalate_reviewer": False,
            },
        ]
    )

    monkeypatch.setattr(
        "app.services.inbox.reply_classification_service.llm_classify_inbound_reply",
        lambda **kwargs: next(responses),
    )

    resp = client.post("/api/v1/mail/inbound/messages/classify-pending?limit=10")
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 2
    assert {item["classification_status"] for item in payload} == {
        InboundMailClassificationStatus.CLASSIFIED.value
    }
    assert {item["classification_label"] for item in payload}.issubset(VALID_REPLY_LABELS)
    escalated = [item for item in payload if item["classification_label"] == "needs_human_review"][0]
    assert escalated["should_escalate_reviewer"] is True

    filtered = client.get("/api/v1/mail/inbound/messages?classification_status=classified")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 2
