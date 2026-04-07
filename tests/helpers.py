"""Shared test-data seeding helpers used across inbound mail test modules."""

from datetime import UTC, datetime


def create_sent_delivery(
    db,
    *,
    recipient_email: str = "owner@example.com",
    provider_message_id: str = "out-123",
    subject: str = "Approved subject",
):
    from app.models.lead import Lead, LeadStatus
    from app.models.outreach import DraftStatus, OutreachDraft
    from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus

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


def message_payload(
    *,
    provider_message_id: str,
    message_id: str,
    in_reply_to: str | None = None,
    references_raw: str | None = None,
    from_email: str = "owner@example.com",
    subject: str = "Re: Approved subject",
    body_text: str = "Hola, me interesa seguir conversando.",
):
    from app.mail.inbound_provider import InboundMailMessage

    return InboundMailMessage(
        provider="imap",
        provider_mailbox="INBOX",
        provider_message_id=provider_message_id,
        message_id=message_id,
        in_reply_to=in_reply_to,
        references_raw=references_raw,
        from_email=from_email,
        from_name="Owner",
        to_email="ops@scouter.local",
        subject=subject,
        body_text=body_text,
        body_snippet=body_text[:80],
        received_at=datetime(2026, 3, 13, 11, 0, tzinfo=UTC),
        raw_metadata={"uid": provider_message_id},
    )
