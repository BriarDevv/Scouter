from datetime import UTC, datetime
import uuid

from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.mail.provider import MailSendResult
from app.models.mail_credentials import MailCredentials
from app.models.inbound_mail import (
    EmailThread,
    InboundMailClassificationStatus,
    InboundMessage,
)
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus
from app.models.reply_assistant import ReplyAssistantDraft
from app.models.reply_assistant_send import ReplyAssistantSend, ReplyAssistantSendStatus
from app.models.settings import OperationalSettings


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
        to_email="ops@scouter.local",
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


def _configure_reply_send_mail(db):
    db.merge(
        OperationalSettings(
            id=1,
            mail_enabled=True,
            mail_from_email="ops@scouter.local",
            mail_from_name="Scouter Ops",
            mail_reply_to="reply@scouter.local",
            mail_send_timeout_seconds=30,
        )
    )
    db.merge(
        MailCredentials(
            id=1,
            smtp_host="smtp.local",
            smtp_port=587,
            smtp_username="ops@scouter.local",
            smtp_password="super-secret",
            smtp_starttls=True,
            smtp_ssl=False,
        )
    )
    db.commit()


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
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
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
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
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
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
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
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
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

    monkeypatch.setattr("app.services.inbox.reply_response_service.get_brand_context", lambda db: {})
    monkeypatch.setattr(db, "commit", flaky_commit)

    resp = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["body"] == "Versión final después del race."
    assert payload["subject"] == "Re: Seguimiento sitio web"
    assert db.query(ReplyAssistantDraft).count() == 1


def test_patch_reply_assistant_draft_persists_edit_metadata(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)
    monkeypatch.setattr(
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Re: Seguimiento sitio web",
            "body": "Versión inicial.",
            "summary": "Draft base.",
            "suggested_tone": "consultative",
            "should_escalate_reviewer": False,
        },
    )
    create_resp = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert create_resp.status_code == 200

    patch_resp = client.patch(
        f"/api/v1/replies/{message.id}/draft-response",
        json={
            "subject": "Re: Seguimiento sitio web - propuesta breve",
            "body": "Te comparto una propuesta breve con siguientes pasos.",
            "edited_by": "ops-user",
        },
    )
    assert patch_resp.status_code == 200
    payload = patch_resp.json()
    assert payload["subject"] == "Re: Seguimiento sitio web - propuesta breve"
    assert payload["edited_by"] == "ops-user"
    assert payload["edited_at"] is not None


def test_send_reply_assistant_draft_persists_send_and_threading_headers(client, db, monkeypatch):
    _, _, _, thread, message = _seed_inbound_reply(db)
    _configure_reply_send_mail(db)

    monkeypatch.setattr(
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Seguimiento sitio web",
            "body": "Claro, te comparto una propuesta breve.",
            "summary": "Respuesta con propuesta.",
            "suggested_tone": "consultative",
            "should_escalate_reviewer": False,
        },
    )

    sent_requests = []

    class FakeProvider:
        def send_email(self, request):
            sent_requests.append(request)
            return MailSendResult(
                provider="smtp",
                provider_message_id="reply-send-001",
                recipient_email=request.recipient_email,
                sent_at=datetime(2026, 3, 14, 14, 0, tzinfo=UTC),
            )

    monkeypatch.setattr("app.services.outreach.mail_service.get_mail_provider", lambda: FakeProvider())

    create_resp = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert create_resp.status_code == 200

    send_resp = client.post(f"/api/v1/replies/{message.id}/draft-response/send")
    assert send_resp.status_code == 200
    payload = send_resp.json()
    assert payload["thread_id"] == str(thread.id)
    assert payload["status"] == ReplyAssistantSendStatus.SENT.value
    assert payload["provider_message_id"] == "reply-send-001"
    assert payload["recipient_email"] == "owner@example.com"
    assert payload["in_reply_to"] == "msg-001@example.com"
    assert payload["references_raw"] == "provider-msg-001 msg-001@example.com"
    assert sent_requests[0].in_reply_to == "msg-001@example.com"
    assert sent_requests[0].references_raw == "provider-msg-001 msg-001@example.com"
    assert sent_requests[0].subject == "Re: Seguimiento sitio web"

    status_resp = client.get(f"/api/v1/replies/{message.id}/draft-response/send-status")
    assert status_resp.status_code == 200
    status_payload = status_resp.json()
    assert status_payload["sent"] is True
    assert status_payload["latest_send"]["provider_message_id"] == "reply-send-001"
    assert status_payload["send_blocked_reason"] == "Reply draft has already been sent."

    saved_send = db.query(ReplyAssistantSend).one()
    assert saved_send.thread_id == thread.id
    assert saved_send.status == ReplyAssistantSendStatus.SENT


def test_send_reply_assistant_draft_blocks_when_review_requires_edits(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)
    _configure_reply_send_mail(db)

    monkeypatch.setattr(
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Re: Seguimiento sitio web",
            "body": "Borrador sin editar.",
            "summary": "Draft base.",
            "suggested_tone": "consultative",
            "should_escalate_reviewer": False,
        },
    )
    client.post(f"/api/v1/replies/{message.id}/draft-response")

    monkeypatch.setattr(
        "app.services.inbox.reply_draft_review_service.llm_review_reply_assistant_draft",
        lambda **kwargs: {
            "summary": "Necesita una edición.",
            "feedback": "Conviene editar antes de enviar.",
            "suggested_edits": ["Ajustar el CTA."],
            "recommended_action": "edit_before_sending",
            "should_use_as_is": False,
            "should_edit": True,
            "should_escalate": False,
        },
    )
    monkeypatch.setattr(
        "app.services.inbox.reply_draft_review_service.resolve_model_for_role",
        lambda role: "qwen3.5:27b",
    )
    from app.services.inbox.reply_draft_review_service import review_reply_assistant_draft_with_reviewer

    review_reply_assistant_draft_with_reviewer(db, message.id)

    send_resp = client.post(f"/api/v1/replies/{message.id}/draft-response/send")
    assert send_resp.status_code == 400
    assert "editing before sending" in send_resp.json()["detail"].lower()


def test_send_reply_assistant_draft_is_idempotent_under_duplicate_clicks(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)
    _configure_reply_send_mail(db)

    monkeypatch.setattr(
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Re: Seguimiento sitio web",
            "body": "Respuesta lista.",
            "summary": "Draft listo.",
            "suggested_tone": "consultative",
            "should_escalate_reviewer": False,
        },
    )

    class FakeProvider:
        def send_email(self, request):
            return MailSendResult(
                provider="smtp",
                provider_message_id="reply-send-unique",
                recipient_email=request.recipient_email,
                sent_at=datetime(2026, 3, 14, 14, 0, tzinfo=UTC),
            )

    monkeypatch.setattr("app.services.outreach.mail_service.get_mail_provider", lambda: FakeProvider())
    client.post(f"/api/v1/replies/{message.id}/draft-response")

    first = client.post(f"/api/v1/replies/{message.id}/draft-response/send")
    second = client.post(f"/api/v1/replies/{message.id}/draft-response/send")
    assert first.status_code == 200
    assert second.status_code == 409
    assert db.query(ReplyAssistantSend).count() == 1
