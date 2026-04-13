from datetime import UTC, datetime, timedelta

from helpers import create_sent_delivery, message_payload

from app.core.config import settings
from app.models.inbound_mail import EmailThread, InboundMailClassificationStatus, InboundMessage
from app.models.reply_assistant import ReplyAssistantDraft
from app.models.reply_assistant_send import ReplyAssistantSend, ReplyAssistantSendStatus


def _create_sent_reply_send(db, *, recipient_email: str = "owner@example.com"):
    lead, draft, delivery = create_sent_delivery(db, recipient_email=recipient_email)
    recent = datetime.now(UTC) - timedelta(days=1)
    thread = EmailThread(
        lead_id=lead.id,
        draft_id=draft.id,
        delivery_id=delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        external_thread_id="thread-reply-send",
        thread_key="thread-reply-send-key",
        matched_via="message_id",
        match_confidence=1.0,
        last_message_at=recent,
    )
    db.add(thread)
    db.flush()

    inbound = InboundMessage(
        dedupe_key="imap:INBOX:reply-origin-001",
        thread_id=thread.id,
        lead_id=lead.id,
        draft_id=draft.id,
        delivery_id=delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        provider_message_id="reply-origin-001",
        message_id="<reply-origin-001@example.com>",
        in_reply_to="<out-123>",
        references_raw="<out-123>",
        from_email=recipient_email,
        from_name="Owner",
        to_email="ops@scouter.local",
        subject="Re: Approved subject",
        body_text="Hola, gracias.",
        body_snippet="Hola, gracias.",
        received_at=recent,
        raw_metadata_json={"uid": "reply-origin-001"},
        classification_status=InboundMailClassificationStatus.PENDING.value,
    )
    db.add(inbound)
    db.flush()

    reply_draft = ReplyAssistantDraft(
        inbound_message_id=inbound.id,
        thread_id=thread.id,
        lead_id=lead.id,
        related_delivery_id=delivery.id,
        related_outbound_draft_id=draft.id,
        status="generated",
        subject="Re: Approved subject",
        body="Gracias por responder.",
        summary="Draft reply.",
        suggested_tone="warm",
        should_escalate_reviewer=False,
        generator_role="executor",
        generator_model="qwen3.5:9b",
    )
    db.add(reply_draft)
    db.flush()

    reply_send = ReplyAssistantSend(
        reply_assistant_draft_id=reply_draft.id,
        inbound_message_id=inbound.id,
        thread_id=thread.id,
        lead_id=lead.id,
        status=ReplyAssistantSendStatus.SENT,
        provider="smtp",
        provider_message_id="reply-send-anchor-001",
        recipient_email=recipient_email,
        from_email_snapshot="ops@scouter.local",
        reply_to_snapshot="reply@scouter.local",
        subject_snapshot="Re: Approved subject",
        body_snapshot="Gracias por responder.",
        in_reply_to="reply-origin-001@example.com",
        references_raw="out-123 reply-origin-001@example.com",
        sent_at=recent,
    )
    db.add(reply_send)
    db.commit()
    return lead, draft, delivery, thread, inbound, reply_draft, reply_send


def test_inbound_sync_blocked_when_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", False)

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 503
    assert "deshabilitada" in resp.json()["detail"].lower()


def test_inbound_sync_deduplicates_and_matches_by_message_id(client, db, monkeypatch):
    lead, draft, delivery = create_sent_delivery(db, provider_message_id="out-abc")
    payload = message_payload(
        provider_message_id="imap-001",
        message_id="<reply-001@example.com>",
        in_reply_to="<out-abc>",
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            assert limit == settings.MAIL_INBOUND_SYNC_LIMIT
            return [payload]

    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr(
        "app.services.inbox.inbound_mail_service.get_inbound_provider", lambda: FakeProvider()
    )

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 200
    sync_payload = resp.json()
    assert sync_payload["fetched_count"] == 1
    assert sync_payload["new_count"] == 1
    assert sync_payload["deduplicated_count"] == 0
    assert sync_payload["matched_count"] == 1
    assert sync_payload["unmatched_count"] == 0

    messages = client.get("/api/v1/mail/inbound/messages")
    assert messages.status_code == 200
    items = messages.json()
    assert len(items) == 1
    assert items[0]["lead_id"] == str(lead.id)
    assert items[0]["draft_id"] == str(draft.id)
    assert items[0]["delivery_id"] == str(delivery.id)
    assert items[0]["classification_status"] == InboundMailClassificationStatus.PENDING.value

    threads = client.get("/api/v1/mail/inbound/threads")
    assert threads.status_code == 200
    thread_payload = threads.json()
    assert len(thread_payload) == 1
    assert thread_payload[0]["matched_via"] == "message_id"
    assert thread_payload[0]["match_confidence"] == 1.0
    assert thread_payload[0]["message_count"] == 1

    logs = client.get(f"/api/v1/outreach/logs?lead_id={lead.id}")
    assert logs.status_code == 200
    assert logs.json()[0]["action"] == "replied"

    resp_second = client.post("/api/v1/mail/inbound/sync")
    assert resp_second.status_code == 200
    sync_second_payload = resp_second.json()
    assert sync_second_payload["fetched_count"] == 1
    assert sync_second_payload["new_count"] == 0
    assert sync_second_payload["deduplicated_count"] == 1
    assert sync_second_payload["matched_count"] == 0


def test_inbound_sync_matches_by_references(client, db, monkeypatch):
    lead, draft, delivery = create_sent_delivery(db, provider_message_id="out-ref-123")
    payload = message_payload(
        provider_message_id="imap-002",
        message_id="<reply-002@example.com>",
        references_raw="<something@example.com> <out-ref-123>",
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            return [payload]

    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr(
        "app.services.inbox.inbound_mail_service.get_inbound_provider", lambda: FakeProvider()
    )

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 1

    thread = client.get("/api/v1/mail/inbound/threads").json()[0]
    assert thread["lead_id"] == str(lead.id)
    assert thread["draft_id"] == str(draft.id)
    assert thread["delivery_id"] == str(delivery.id)
    assert thread["matched_via"] == "references"
    assert thread["match_confidence"] == 0.9


def test_inbound_sync_falls_back_to_subject_and_email(client, db, monkeypatch):
    lead, draft, delivery = create_sent_delivery(db, provider_message_id="out-fallback")
    payload = message_payload(
        provider_message_id="imap-003",
        message_id="<reply-003@example.com>",
        subject="Re: Approved subject",
        in_reply_to=None,
        references_raw=None,
        from_email=lead.email,
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            return [payload]

    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr(
        "app.services.inbox.inbound_mail_service.get_inbound_provider", lambda: FakeProvider()
    )

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 1

    thread = client.get("/api/v1/mail/inbound/threads").json()[0]
    assert thread["lead_id"] == str(lead.id)
    assert thread["draft_id"] == str(draft.id)
    assert thread["delivery_id"] == str(delivery.id)
    assert thread["matched_via"] == "subject_fallback"
    assert thread["match_confidence"] == 0.3  # CC-8: lowered from 0.4


def test_inbound_status_and_detail_endpoints(client, db, monkeypatch):
    create_sent_delivery(db, provider_message_id="out-status")
    payload = message_payload(
        provider_message_id="imap-004",
        message_id="<reply-004@example.com>",
        in_reply_to="<out-status>",
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            return [payload]

    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr(settings, "MAIL_AUTO_CLASSIFY_INBOUND", False)
    monkeypatch.setattr(
        settings, "MAIL_USE_REVIEWER_FOR_LABELS", "asked_for_quote,needs_human_review"
    )
    monkeypatch.setattr(
        "app.services.inbox.inbound_mail_service.get_inbound_provider", lambda: FakeProvider()
    )

    sync_resp = client.post("/api/v1/mail/inbound/sync")
    assert sync_resp.status_code == 200

    status_resp = client.get("/api/v1/mail/inbound/status")
    assert status_resp.status_code == 200
    status_payload = status_resp.json()
    assert status_payload["enabled"] is True
    assert status_payload["provider"] == "imap"
    assert status_payload["auto_classify_inbound"] is False
    assert status_payload["reviewer_labels"] == ["asked_for_quote", "needs_human_review"]
    assert status_payload["last_sync"]["status"] == "completed"

    message = client.get("/api/v1/mail/inbound/messages").json()[0]
    detail_resp = client.get(f"/api/v1/mail/inbound/messages/{message['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["message_id"] == "reply-004@example.com"

    thread = client.get("/api/v1/mail/inbound/threads").json()[0]
    thread_detail_resp = client.get(f"/api/v1/mail/inbound/threads/{thread['id']}")
    assert thread_detail_resp.status_code == 200
    assert len(thread_detail_resp.json()["messages"]) == 1


def test_inbound_sync_matches_reply_assistant_send_message_ids(client, db, monkeypatch):
    lead, _, _, thread, _, _, reply_send = _create_sent_reply_send(db)
    payload = message_payload(
        provider_message_id="imap-reply-followup-001",
        message_id="<followup-001@example.com>",
        in_reply_to=f"<{reply_send.provider_message_id}>",
        subject="Re: Approved subject",
        from_email=lead.email,
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            return [payload]

    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr(
        "app.services.inbox.inbound_mail_service.get_inbound_provider", lambda: FakeProvider()
    )

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 1

    messages = client.get("/api/v1/mail/inbound/messages").json()
    matched = next(
        item for item in messages if item["provider_message_id"] == "imap-reply-followup-001"
    )
    assert matched["thread_id"] == str(thread.id)
    assert matched["lead_id"] == str(lead.id)
    assert matched["delivery_id"] is None

    thread_payload = client.get("/api/v1/mail/inbound/threads").json()[0]
    assert thread_payload["id"] == str(thread.id)
    assert thread_payload["matched_via"] == "message_id"
