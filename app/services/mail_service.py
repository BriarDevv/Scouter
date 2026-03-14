from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.mail.provider import MailProviderError, MailSendRequest, MailSendResult
from app.mail.smtp_provider import SMTPMailProvider
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus
from app.services.mail_credentials_service import get_effective_smtp
from app.services.operational_settings_service import get_effective_mail_outbound, get_or_create
from app.services.outreach_service import update_draft

logger = get_logger(__name__)


class MailServiceError(RuntimeError):
    """Base mail service error."""


class MailDisabledError(MailServiceError):
    """Raised when mail sending is disabled."""


class MailConfigurationError(MailServiceError):
    """Raised when effective mail configuration is incomplete."""


class DraftNotApprovedError(MailServiceError):
    """Raised when a draft is not approved for sending."""


class DraftRecipientMissingError(MailServiceError):
    """Raised when the lead has no recipient email."""


class DraftAlreadySentError(MailServiceError):
    """Raised when a draft has already been sent."""


@dataclass(frozen=True)
class EffectiveOutboundMailConfig:
    provider: str
    enabled: bool
    from_email: str | None
    from_name: str
    reply_to: str | None
    timeout_seconds: int
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_ssl: bool
    smtp_starttls: bool


def get_mail_provider(provider_name: str | None = None) -> SMTPMailProvider:
    selected_provider = (provider_name or settings.MAIL_PROVIDER).lower()
    if selected_provider != "smtp":
        raise MailProviderError(f"Unsupported MAIL_PROVIDER {selected_provider!r}.")
    return SMTPMailProvider()


def get_effective_outbound_mail_config(db: Session) -> EffectiveOutboundMailConfig:
    operational_row = get_or_create(db)
    outbound = get_effective_mail_outbound(operational_row)
    smtp = get_effective_smtp(db)
    return EffectiveOutboundMailConfig(
        provider=settings.MAIL_PROVIDER.lower(),
        enabled=bool(outbound["enabled"]),
        from_email=((outbound["from_email"] or "").strip() or None),
        from_name=(outbound["from_name"] or settings.MAIL_FROM_NAME).strip(),
        reply_to=((outbound["reply_to"] or "").strip() or None),
        timeout_seconds=int(outbound["send_timeout_seconds"]),
        smtp_host=((smtp.host or "").strip() or None),
        smtp_port=int(smtp.port),
        smtp_username=((smtp.username or "").strip() or None),
        smtp_password=smtp.password,
        smtp_ssl=bool(smtp.ssl),
        smtp_starttls=bool(smtp.starttls),
    )


def ensure_outbound_mail_ready(db: Session) -> EffectiveOutboundMailConfig:
    config = get_effective_outbound_mail_config(db)
    if not config.enabled:
        raise MailDisabledError(
            "Mail sending is disabled. Set MAIL_ENABLED=true or enable the DB override to allow delivery."
        )

    missing_requirements: list[str] = []
    if not config.from_email:
        missing_requirements.append("from_email")
    if not config.smtp_host:
        missing_requirements.append("smtp_host")
    if bool(config.smtp_username) != bool(config.smtp_password):
        missing_requirements.append("smtp_credentials_pair")
    if config.smtp_ssl and config.smtp_starttls:
        missing_requirements.append("smtp_ssl_starttls_conflict")

    if missing_requirements:
        joined = ", ".join(missing_requirements)
        raise MailConfigurationError(f"Mail configuration is incomplete: {joined}.")
    return config


def build_mail_send_request(
    *,
    config: EffectiveOutboundMailConfig,
    recipient_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None = None,
    references_raw: str | None = None,
) -> MailSendRequest:
    return MailSendRequest(
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        from_email=config.from_email or "",
        from_name=config.from_name,
        reply_to=config.reply_to,
        timeout_seconds=config.timeout_seconds,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        smtp_username=config.smtp_username,
        smtp_password=config.smtp_password,
        smtp_ssl=config.smtp_ssl,
        smtp_starttls=config.smtp_starttls,
        in_reply_to=in_reply_to,
        references_raw=references_raw,
    )


def send_mail(request: MailSendRequest, *, provider_name: str | None = None) -> MailSendResult:
    provider = get_mail_provider(provider_name) if provider_name is not None else get_mail_provider()
    return provider.send_email(request)


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
    config = ensure_outbound_mail_ready(db)

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
        provider=config.provider,
        recipient_email=recipient_email,
        subject_snapshot=draft.subject,
        status=OutreachDeliveryStatus.SENDING,
    )
    db.add(delivery)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Re-check state after rollback
        db.refresh(draft)
        if draft.status == DraftStatus.SENT:
            raise DraftAlreadySentError("Draft has already been sent.")
        raise DraftAlreadySentError("Draft send is already in progress.")
    db.refresh(delivery)

    request = build_mail_send_request(
        config=config,
        recipient_email=recipient_email,
        subject=draft.subject,
        body=draft.body,
    )

    try:
        result = send_mail(request)
    except MailProviderError as exc:
        delivery.status = OutreachDeliveryStatus.FAILED
        delivery.error = str(exc)
        db.commit()
        db.refresh(delivery)
        try:
            from app.services.notification_emitter import on_send_failed
            on_send_failed(db, delivery_id=delivery.id, recipient=delivery.recipient_email, error=delivery.error, send_type="outreach")
        except Exception:
            pass
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
