from datetime import UTC, datetime
import uuid

from app.core.config import settings
from app.mail.provider import MailProviderError, MailSendResult
from app.models.lead import Lead, LeadStatus
from app.models.mail_credentials import MailCredentials
from app.models.settings import OperationalSettings
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus


def _create_approved_draft(db, *, email: str | None = "owner@example.com"):
    lead = Lead(
        business_name="Mail Lead",
        city="Cordoba",
        email=email,
        status=LeadStatus.APPROVED,
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Approved subject",
        body="Approved body",
        status=DraftStatus.APPROVED,
    )
    db.add(draft)
    db.commit()
    return lead, draft


def _configure_db_mail(db):
    db.merge(
        OperationalSettings(
            id=1,
            mail_enabled=True,
            mail_from_email="ops@scouter.local",
            mail_from_name="Scouter Ops",
            mail_reply_to="reply@scouter.local",
            mail_send_timeout_seconds=45,
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


def test_get_draft_detail_endpoint(client, db):
    _, draft = _create_approved_draft(db)

    resp = client.get(f"/api/v1/outreach/drafts/{draft.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] == str(draft.id)
    assert payload["subject"] == "Approved subject"
    assert payload["status"] == "approved"


def test_send_draft_blocked_when_mail_disabled(client, db):
    _, draft = _create_approved_draft(db)

    resp = client.post(f"/api/v1/outreach/drafts/{draft.id}/send")
    assert resp.status_code == 503
    assert "MAIL_ENABLED=true" in resp.json()["detail"]


def test_send_draft_blocked_when_not_approved(client, db, monkeypatch):
    lead = Lead(
        business_name="Pending Mail Lead",
        city="Rosario",
        email="hello@example.com",
        status=LeadStatus.DRAFT_READY,
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Pending subject",
        body="Pending body",
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)
    db.commit()

    _configure_db_mail(db)

    resp = client.post(f"/api/v1/outreach/drafts/{draft.id}/send")
    assert resp.status_code == 409
    assert "approved" in resp.json()["detail"].lower()


def test_send_draft_success_persists_delivery_and_updates_state(client, db, monkeypatch):
    lead, draft = _create_approved_draft(db)
    _configure_db_mail(db)

    class FakeProvider:
        def send_email(self, request):
            return MailSendResult(
                provider="smtp",
                provider_message_id="msg-123",
                recipient_email=request.recipient_email,
                sent_at=datetime(2026, 3, 13, 6, 15, tzinfo=UTC),
            )

    monkeypatch.setattr(settings, "MAIL_ENABLED", False)
    monkeypatch.setattr(settings, "MAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "MAIL_SMTP_HOST", None)
    monkeypatch.setattr("app.services.outreach.mail_service.get_mail_provider", lambda: FakeProvider())

    resp = client.post(f"/api/v1/outreach/drafts/{draft.id}/send")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["draft_id"] == str(draft.id)
    assert payload["lead_id"] == str(lead.id)
    assert payload["provider"] == "smtp"
    assert payload["provider_message_id"] == "msg-123"
    assert payload["recipient_email"] == "owner@example.com"
    assert payload["status"] == OutreachDeliveryStatus.SENT.value
    assert payload["sent_at"] is not None

    refreshed_draft = db.get(OutreachDraft, draft.id)
    assert refreshed_draft is not None
    assert refreshed_draft.status == DraftStatus.SENT
    assert refreshed_draft.sent_at is not None

    deliveries = client.get(f"/api/v1/outreach/drafts/{draft.id}/deliveries")
    assert deliveries.status_code == 200
    delivery_payload = deliveries.json()
    assert len(delivery_payload) == 1
    assert delivery_payload[0]["provider_message_id"] == "msg-123"

    logs = client.get(f"/api/v1/outreach/logs?draft_id={draft.id}")
    assert logs.status_code == 200
    assert logs.json()[0]["action"] == "sent"
    assert logs.json()[0]["actor"] == "system"


def test_send_draft_failure_persists_failed_delivery(client, db, monkeypatch):
    _, draft = _create_approved_draft(db)
    _configure_db_mail(db)

    class BrokenProvider:
        def send_email(self, request):
            raise MailProviderError("smtp unavailable")

    monkeypatch.setattr(settings, "MAIL_ENABLED", False)
    monkeypatch.setattr(settings, "MAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "MAIL_SMTP_HOST", None)
    monkeypatch.setattr("app.services.outreach.mail_service.get_mail_provider", lambda: BrokenProvider())

    resp = client.post(f"/api/v1/outreach/drafts/{draft.id}/send")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == OutreachDeliveryStatus.FAILED.value
    assert payload["error"] == "smtp unavailable"

    refreshed_draft = db.get(OutreachDraft, draft.id)
    assert refreshed_draft is not None
    assert refreshed_draft.status == DraftStatus.APPROVED
    assert refreshed_draft.sent_at is None

    delivery = db.get(OutreachDelivery, uuid.UUID(payload["id"]))
    assert delivery is not None
    assert delivery.status == OutreachDeliveryStatus.FAILED
    assert delivery.error == "smtp unavailable"


def test_send_draft_rate_limited_after_3_failures(client, db):
    """CC-7: re-send should be blocked after 3 failed deliveries."""
    lead, draft = _create_approved_draft(db)
    _configure_db_mail(db)

    # Add 3 failed deliveries
    for _ in range(3):
        d = OutreachDelivery(
            lead_id=lead.id,
            draft_id=draft.id,
            provider="smtp",
            recipient_email="owner@example.com",
            subject_snapshot="Approved subject",
            status=OutreachDeliveryStatus.FAILED,
            error="test failure",
        )
        db.add(d)
    db.commit()

    # Attempting to send should fail with rate limit
    resp = client.post(f"/api/v1/outreach/drafts/{draft.id}/send")
    assert resp.status_code == 429
    assert "intentos fallidos" in resp.json()["detail"].lower()


def test_outreach_delivery_enum_uses_lowercase_values():
    enum_values = list(OutreachDelivery.__table__.c.status.type.enums)
    assert enum_values == ["sending", "sent", "failed"]
