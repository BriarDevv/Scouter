from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.mail.provider import MailProviderError, MailSendRequest
from app.mail.smtp_provider import SMTPMailProvider
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus
from app.services.outreach_service import update_draft

logger = get_logger(__name__)


class MailServiceError(RuntimeError):
    """Base mail service error."""


class MailDisabledError(MailServiceError):
    """Raised when mail sending is disabled."""


class DraftNotApprovedError(MailServiceError):
    """Raised when a draft is not approved for sending."""


class DraftRecipientMissingError(MailServiceError):
    """Raised when the lead has no recipient email."""


class DraftAlreadySentError(MailServiceError):
    """Raised when a draft has already been sent."""


def get_mail_provider() -> SMTPMailProvider:
    if settings.MAIL_PROVIDER.lower() != "smtp":
        raise MailProviderError(f"Unsupported MAIL_PROVIDER {settings.MAIL_PROVIDER!r}.")
    return SMTPMailProvider()


def get_draft(db: Session, draft_id: uuid.UUID) -> OutreachDraft | None:
    return db.get(OutreachDraft, draft_id)


def list_deliveries(db: Session, draft_id: uuid.UUID) -> list[OutreachDelivery]:
    stmt = (
        select(OutreachDelivery)
        .where(OutreachDelivery.draft_id == draft_id)
        .order_by(OutreachDelivery.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def send_draft(db: Session, draft_id: uuid.UUID) -> OutreachDelivery | None:
    if not settings.MAIL_ENABLED:
        raise MailDisabledError("Mail sending is disabled. Set MAIL_ENABLED=true to allow delivery.")

    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        return None

    if draft.status == DraftStatus.SENT:
        raise DraftAlreadySentError("Draft has already been sent.")
    if draft.status != DraftStatus.APPROVED:
        raise DraftNotApprovedError("Draft must be approved before sending.")

    lead = draft.lead
    recipient_email = (lead.email or "").strip() if lead else ""
    if not recipient_email:
        raise DraftRecipientMissingError("Lead does not have a recipient email.")

    delivery = OutreachDelivery(
        lead_id=draft.lead_id,
        draft_id=draft.id,
        provider=settings.MAIL_PROVIDER.lower(),
        recipient_email=recipient_email,
        subject_snapshot=draft.subject,
        status=OutreachDeliveryStatus.SENDING,
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    request = MailSendRequest(
        recipient_email=recipient_email,
        subject=draft.subject,
        body=draft.body,
        from_email=(settings.MAIL_FROM_EMAIL or "").strip(),
        from_name=settings.MAIL_FROM_NAME.strip(),
        reply_to=(settings.MAIL_REPLY_TO or "").strip() or None,
        timeout_seconds=settings.MAIL_SEND_TIMEOUT,
    )

    try:
        provider = get_mail_provider()
        result = provider.send_email(request)
    except MailProviderError as exc:
        delivery.status = OutreachDeliveryStatus.FAILED
        delivery.error = str(exc)
        db.commit()
        db.refresh(delivery)
        logger.warning(
            "mail_delivery_failed",
            delivery_id=str(delivery.id),
            lead_id=str(delivery.lead_id),
            draft_id=str(delivery.draft_id),
            provider=delivery.provider,
            recipient_email=delivery.recipient_email,
            error=delivery.error,
        )
        return delivery

    delivery.status = OutreachDeliveryStatus.SENT
    delivery.provider = result.provider
    delivery.provider_message_id = result.provider_message_id
    delivery.sent_at = result.sent_at
    delivery.error = None

    update_draft(db, draft_id, status=DraftStatus.SENT, actor="system")
    db.refresh(delivery)

    logger.info(
        "mail_delivery_sent",
        delivery_id=str(delivery.id),
        lead_id=str(delivery.lead_id),
        draft_id=str(delivery.draft_id),
        provider=delivery.provider,
        provider_message_id=delivery.provider_message_id,
        recipient_email=delivery.recipient_email,
    )
    return delivery
