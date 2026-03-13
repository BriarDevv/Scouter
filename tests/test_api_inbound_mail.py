from datetime import UTC, datetime

from app.core.config import settings
from app.mail.inbound_provider import InboundMailMessage
from app.models.inbound_mail import InboundMailClassificationStatus
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus


def _create_sent_delivery(
    db,
    *,
    recipient_email: str = "owner@example.com",
    provider_message_id: str = "out-123",
    subject: str = "Approved subject",
):
    lead = Lead(
        business_name="Inbound Lead",
        city="Cordoba",
        email=recipient_email,
        status=LeadStatus.CONTACTED,
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject=subject,
        body="Draft body",
        status=DraftStatus.SENT,
        sent_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    db.add(draft)
    db.flush()

    delivery = OutreachDelivery(
        lead_id=lead.id,
        draft_id=draft.id,
        provider="smtp",
        provider_message_id=provider_message_id,
        recipient_email=recipient_email,
        subject_snapshot=subject,
        status=OutreachDeliveryStatus.SENT,
        sent_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    db.add(delivery)
    db.commit()
    return lead, draft, delivery


def _message_payload(
    *,
    provider_message_id: str,
    message_id: str,
    in_reply_to: str | None = None,
    references_raw: str | None = None,
    from_email: str = "owner@example.com",
    subject: str = "Re: Approved subject",
    body_text: str = "Hola, me interesa seguir conversando.",
):
    return InboundMailMessage(
        provider="imap",
        provider_mailbox="INBOX",
        provider_message_id=provider_message_id,
        message_id=message_id,
        in_reply_to=in_reply_to,
        references_raw=references_raw,
        from_email=from_email,
        from_name="Owner",
        to_email="ops@clawscout.local",
        subject=subject,
        body_text=body_text,
        body_snippet=body_text[:80],
        received_at=datetime(2026, 3, 13, 11, 0, tzinfo=UTC),
        raw_metadata={"uid": provider_message_id},
    )


def test_inbound_sync_blocked_when_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", False)

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 503
    assert "MAIL_INBOUND_ENABLED=true" in resp.json()["detail"]


def test_inbound_sync_deduplicates_and_matches_by_message_id(client, db, monkeypatch):
    lead, draft, delivery = _create_sent_delivery(db, provider_message_id="out-abc")
    payload = _message_payload(
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
    monkeypatch.setattr("app.services.inbound_mail_service.get_inbound_provider", lambda: FakeProvider())

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
    lead, draft, delivery = _create_sent_delivery(db, provider_message_id="out-ref-123")
    payload = _message_payload(
        provider_message_id="imap-002",
        message_id="<reply-002@example.com>",
        references_raw="<something@example.com> <out-ref-123>",
    )

    class FakeProvider:
        name = "imap"

        def list_messages(self, *, limit: int):
            return [payload]

    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr("app.services.inbound_mail_service.get_inbound_provider", lambda: FakeProvider())

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
    lead, draft, delivery = _create_sent_delivery(db, provider_message_id="out-fallback")
    payload = _message_payload(
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
    monkeypatch.setattr("app.services.inbound_mail_service.get_inbound_provider", lambda: FakeProvider())

    resp = client.post("/api/v1/mail/inbound/sync")
    assert resp.status_code == 200
    assert resp.json()["matched_count"] == 1

    thread = client.get("/api/v1/mail/inbound/threads").json()[0]
    assert thread["lead_id"] == str(lead.id)
    assert thread["draft_id"] == str(draft.id)
    assert thread["delivery_id"] == str(delivery.id)
    assert thread["matched_via"] == "subject_fallback"
    assert thread["match_confidence"] == 0.55


def test_inbound_status_and_detail_endpoints(client, db, monkeypatch):
    _create_sent_delivery(db, provider_message_id="out-status")
    payload = _message_payload(
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
    monkeypatch.setattr(settings, "MAIL_USE_REVIEWER_FOR_LABELS", "asked_for_quote,needs_human_review")
    monkeypatch.setattr("app.services.inbound_mail_service.get_inbound_provider", lambda: FakeProvider())

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
