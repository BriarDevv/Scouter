from datetime import UTC, datetime
import uuid

from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.inbound_mail import (
    EmailThread,
    InboundMailClassificationStatus,
    InboundMessage,
)
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus
from app.models.reply_assistant import ReplyAssistantDraft


def _seed_inbound_reply(db):
    lead = Lead(
        business_name="Reply Draft Lead",
        city="Cordoba",
        email="owner@example.com",
        status=LeadStatus.REPLIED,
        llm_summary="Restaurante familiar con presencia web básica.",
    )
    db.add(lead)
    db.flush()

    outbound_draft = OutreachDraft(
        lead_id=lead.id,
        subject="Seguimiento sitio web",
        body="Hola, te escribo para conversar sobre mejoras en tu sitio.",
        status=DraftStatus.SENT,
        sent_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    db.add(outbound_draft)
    db.flush()

    delivery = OutreachDelivery(
        lead_id=lead.id,
        draft_id=outbound_draft.id,
        provider="smtp",
        provider_message_id="provider-msg-001",
        recipient_email=lead.email,
        subject_snapshot=outbound_draft.subject,
        status=OutreachDeliveryStatus.SENT,
        sent_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    db.add(delivery)
    db.flush()

    thread = EmailThread(
        lead_id=lead.id,
        draft_id=outbound_draft.id,
        delivery_id=delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        external_thread_id="thread-001",
        thread_key="thread-key-001",
        matched_via="message_id",
        match_confidence=1.0,
        last_message_at=datetime(2026, 3, 13, 11, 0, tzinfo=UTC),
    )
    db.add(thread)
    db.flush()

    message = InboundMessage(
        dedupe_key="imap:INBOX:provider-inbound-001",
        thread_id=thread.id,
        lead_id=lead.id,
        draft_id=outbound_draft.id,
        delivery_id=delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        provider_message_id="provider-inbound-001",
        message_id="<msg-001@example.com>",
        in_reply_to="<provider-msg-001>",
        references_raw="<provider-msg-001>",
        from_email=lead.email,
        from_name="Owner",
        to_email="ops@clawscout.local",
        subject="Re: Seguimiento sitio web",
        body_text="Hola, me interesa. ¿Podés pasarme una propuesta breve?",
        body_snippet="Hola, me interesa. ¿Podés pasarme una propuesta breve?",
        received_at=datetime(2026, 3, 13, 11, 0, tzinfo=UTC),
        raw_metadata_json={"uid": "123"},
        classification_status=InboundMailClassificationStatus.CLASSIFIED.value,
        classification_label="asked_for_quote",
        summary="El lead está interesado y pidió una propuesta.",
        confidence=0.92,
        next_action_suggestion="Responder con una propuesta breve y siguientes pasos.",
        should_escalate_reviewer=False,
        classification_role="executor",
        classification_model="qwen3.5:9b",
        classified_at=datetime(2026, 3, 13, 11, 5, tzinfo=UTC),
    )
    db.add(message)
    db.commit()
    return lead, outbound_draft, delivery, thread, message


def test_generate_reply_assistant_draft_persists_result(client, db, monkeypatch):
    lead, outbound_draft, delivery, thread, message = _seed_inbound_reply(db)

    def fake_generate(**kwargs):
        return {
            "subject": "Re: Seguimiento sitio web",
            "body": "Hola, claro. Te comparto una propuesta breve y coordinamos próximos pasos.",
            "summary": "Responde al pedido de propuesta con una continuación comercial breve.",
            "suggested_tone": "consultative",
            "should_escalate_reviewer": False,
        }

    monkeypatch.setattr(
        "app.services.reply_response_service.llm_generate_reply_assistant_draft",
        fake_generate,
    )

    resp = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["inbound_message_id"] == str(message.id)
    assert payload["thread_id"] == str(thread.id)
    assert payload["lead_id"] == str(lead.id)
    assert payload["related_delivery_id"] == str(delivery.id)
    assert payload["related_outbound_draft_id"] == str(outbound_draft.id)
    assert payload["status"] == "generated"
    assert payload["subject"] == "Re: Seguimiento sitio web"
    assert payload["suggested_tone"] == "consultative"
    assert payload["generator_role"] == "executor"
    assert payload["generator_model"] == "qwen3.5:9b"
    assert payload["should_escalate_reviewer"] is False

    saved = db.get(ReplyAssistantDraft, uuid.UUID(payload["id"]))
    assert saved is not None
    assert saved.inbound_message_id == message.id
    assert saved.related_delivery_id == delivery.id
    assert saved.related_outbound_draft_id == outbound_draft.id


def test_get_reply_assistant_draft_returns_existing_record(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)

    monkeypatch.setattr(
        "app.services.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Re: Seguimiento sitio web",
            "body": "Hola, gracias por responder.",
            "summary": "Da una respuesta breve y amable.",
            "suggested_tone": "warm",
            "should_escalate_reviewer": False,
        },
    )
    create_resp = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert create_resp.status_code == 200

    get_resp = client.get(f"/api/v1/replies/{message.id}/draft-response")
    assert get_resp.status_code == 200
    payload = get_resp.json()
    assert payload["inbound_message_id"] == str(message.id)
    assert payload["body"] == "Hola, gracias por responder."


def test_generate_reply_assistant_draft_regenerates_same_record(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)

    responses = iter(
        [
            {
                "subject": "Re: Seguimiento sitio web",
                "body": "Primera versión",
                "summary": "Primer draft",
                "suggested_tone": "brief",
                "should_escalate_reviewer": False,
            },
            {
                "subject": "Re: Seguimiento sitio web",
                "body": "Segunda versión mejorada",
                "summary": "Segundo draft",
                "suggested_tone": "consultative",
                "should_escalate_reviewer": True,
            },
        ]
    )

    monkeypatch.setattr(
        "app.services.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: next(responses),
    )

    first = client.post(f"/api/v1/replies/{message.id}/draft-response")
    second = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["id"] == second_payload["id"]
    assert second_payload["body"] == "Segunda versión mejorada"
    assert second_payload["should_escalate_reviewer"] is True
    assert db.query(ReplyAssistantDraft).count() == 1


def test_generate_reply_assistant_draft_returns_404_for_missing_message(client):
    missing_id = uuid.uuid4()
    resp = client.post(f"/api/v1/replies/{missing_id}/draft-response")
    assert resp.status_code == 404
    assert "Inbound message not found" in resp.json()["detail"]


def test_get_reply_assistant_draft_returns_404_when_absent(client, db):
    _, _, _, _, message = _seed_inbound_reply(db)
    resp = client.get(f"/api/v1/replies/{message.id}/draft-response")
    assert resp.status_code == 404
    assert "Reply assistant draft not found" in resp.json()["detail"]


def test_generate_reply_assistant_draft_handles_concurrent_insert(client, db, monkeypatch):
    lead, outbound_draft, delivery, thread, message = _seed_inbound_reply(db)

    monkeypatch.setattr(
        "app.services.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Re: Seguimiento sitio web",
            "body": "Versión final después del race.",
            "summary": "Draft consolidado después de insert concurrente.",
            "suggested_tone": "professional",
            "should_escalate_reviewer": False,
        },
    )

    original_commit = db.commit
    state = {"raised": False}

    def flaky_commit():
        if not state["raised"]:
            state["raised"] = True
            concurrent_session = SessionLocal()
            try:
                concurrent_session.add(
                    ReplyAssistantDraft(
                        inbound_message_id=message.id,
                        thread_id=thread.id,
                        lead_id=lead.id,
                        related_delivery_id=delivery.id,
                        related_outbound_draft_id=outbound_draft.id,
                        status="generated",
                        subject="Draft concurrente",
                        body="Borrador viejo",
                        summary="Viejo",
                        suggested_tone="brief",
                        should_escalate_reviewer=False,
                        generator_role="executor",
                        generator_model="qwen3.5:9b",
                    )
                )
                concurrent_session.commit()
            finally:
                concurrent_session.close()
            raise IntegrityError("insert", {}, Exception("duplicate"))
        return original_commit()

    monkeypatch.setattr(db, "commit", flaky_commit)

    resp = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["body"] == "Versión final después del race."
    assert payload["subject"] == "Re: Seguimiento sitio web"
    assert db.query(ReplyAssistantDraft).count() == 1
