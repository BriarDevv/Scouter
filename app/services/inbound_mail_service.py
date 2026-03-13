from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.mail.imap_provider import IMAPInboundMailProvider
from app.mail.inbound_provider import InboundMailMessage, InboundMailProviderError
from app.models.inbound_mail import (
    EmailThread,
    InboundMailClassificationStatus,
    InboundMailSyncRun,
    InboundMailSyncStatus,
    InboundMessage,
)
from app.models.outreach import LogAction, OutreachDraft, OutreachLog
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus

logger = get_logger(__name__)

SUBJECT_PREFIX_RE = re.compile(r"^(?:(?:re|fw|fwd)\s*:\s*)+", re.IGNORECASE)
MESSAGE_ID_RE = re.compile(r"<([^>]+)>")


class InboundMailServiceError(RuntimeError):
    """Base inbound mail service error."""


class InboundMailDisabledError(InboundMailServiceError):
    """Raised when inbound sync is disabled."""


@dataclass(frozen=True)
class DeliveryMatch:
    delivery: OutreachDelivery | None
    matched_via: str
    match_confidence: float

    @property
    def lead_id(self) -> uuid.UUID | None:
        return self.delivery.lead_id if self.delivery else None

    @property
    def draft_id(self) -> uuid.UUID | None:
        return self.delivery.draft_id if self.delivery else None

    @property
    def delivery_id(self) -> uuid.UUID | None:
        return self.delivery.id if self.delivery else None


def get_inbound_provider() -> IMAPInboundMailProvider:
    if settings.MAIL_INBOUND_PROVIDER.lower() != "imap":
        raise InboundMailProviderError(
            f"Unsupported MAIL_INBOUND_PROVIDER {settings.MAIL_INBOUND_PROVIDER!r}."
        )
    return IMAPInboundMailProvider()


def list_inbound_messages(
    db: Session,
    *,
    lead_id: uuid.UUID | None = None,
    thread_id: uuid.UUID | None = None,
    classification_status: str | None = None,
    limit: int = 50,
) -> list[InboundMessage]:
    stmt = (
        select(InboundMessage)
        .options(
            selectinload(InboundMessage.thread),
            selectinload(InboundMessage.reply_assistant_draft),
        )
        .order_by(InboundMessage.received_at.desc(), InboundMessage.created_at.desc())
        .limit(limit)
    )
    if lead_id:
        stmt = stmt.where(InboundMessage.lead_id == lead_id)
    if thread_id:
        stmt = stmt.where(InboundMessage.thread_id == thread_id)
    if classification_status:
        stmt = stmt.where(InboundMessage.classification_status == classification_status)
    return list(db.execute(stmt).scalars().all())


def get_inbound_message(db: Session, message_id: uuid.UUID) -> InboundMessage | None:
    stmt = (
        select(InboundMessage)
        .options(
            selectinload(InboundMessage.thread),
            selectinload(InboundMessage.reply_assistant_draft),
        )
        .where(InboundMessage.id == message_id)
    )
    return db.execute(stmt).scalars().first()


def list_email_threads(
    db: Session, *, lead_id: uuid.UUID | None = None, limit: int = 50
) -> list[EmailThread]:
    stmt = (
        select(EmailThread)
        .options(selectinload(EmailThread.messages))
        .order_by(EmailThread.last_message_at.desc(), EmailThread.updated_at.desc())
        .limit(limit)
    )
    if lead_id:
        stmt = stmt.where(EmailThread.lead_id == lead_id)
    return list(db.execute(stmt).scalars().all())


def get_email_thread(db: Session, thread_id: uuid.UUID) -> EmailThread | None:
    stmt = (
        select(EmailThread)
        .options(
            selectinload(EmailThread.messages).selectinload(InboundMessage.reply_assistant_draft)
        )
        .where(EmailThread.id == thread_id)
    )
    return db.execute(stmt).scalars().first()


def get_inbound_sync_status(db: Session) -> InboundMailSyncRun | None:
    stmt = select(InboundMailSyncRun).order_by(InboundMailSyncRun.started_at.desc()).limit(1)
    return db.execute(stmt).scalars().first()


def sync_inbound_messages(db: Session, *, limit: int | None = None) -> InboundMailSyncRun:
    if not settings.MAIL_INBOUND_ENABLED:
        raise InboundMailDisabledError(
            "Inbound mail sync is disabled. Set MAIL_INBOUND_ENABLED=true to allow sync."
        )

    provider = get_inbound_provider()
    sync_run = InboundMailSyncRun(
        provider=provider.name,
        provider_mailbox=settings.MAIL_IMAP_MAILBOX,
        status=InboundMailSyncStatus.RUNNING.value,
    )
    db.add(sync_run)
    db.commit()
    db.refresh(sync_run)

    sync_limit = limit or settings.MAIL_INBOUND_SYNC_LIMIT
    try:
        messages = provider.list_messages(limit=sync_limit)
        sync_run.fetched_count = len(messages)

        for payload in messages:
            persisted_message, result = _persist_inbound_message(db, payload)
            if result == "deduplicated":
                sync_run.deduplicated_count += 1
                continue

            sync_run.new_count += 1
            if result == "matched":
                sync_run.matched_count += 1
            else:
                sync_run.unmatched_count += 1

            if persisted_message and settings.MAIL_AUTO_CLASSIFY_INBOUND:
                from app.services.reply_classification_service import classify_inbound_message

                classify_inbound_message(db, persisted_message.id)

        sync_run.status = InboundMailSyncStatus.COMPLETED.value
        sync_run.error = None
        sync_run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(sync_run)
        logger.info(
            "inbound_mail_sync_completed",
            sync_run_id=str(sync_run.id),
            fetched_count=sync_run.fetched_count,
            new_count=sync_run.new_count,
            deduplicated_count=sync_run.deduplicated_count,
            matched_count=sync_run.matched_count,
            unmatched_count=sync_run.unmatched_count,
        )
        return sync_run
    except InboundMailProviderError as exc:
        sync_run.status = InboundMailSyncStatus.FAILED.value
        sync_run.error = str(exc)
        sync_run.completed_at = datetime.now(UTC)
        db.commit()
        db.refresh(sync_run)
        logger.warning(
            "inbound_mail_sync_failed",
            sync_run_id=str(sync_run.id),
            error=sync_run.error,
        )
        raise


def _persist_inbound_message(
    db: Session, payload: InboundMailMessage
) -> tuple[InboundMessage | None, str]:
    dedupe_key = _build_dedupe_key(payload)
    existing = db.execute(
        select(InboundMessage).where(InboundMessage.dedupe_key == dedupe_key)
    ).scalars().first()
    if existing:
        return None, "deduplicated"

    match = _match_delivery(db, payload)
    thread = _resolve_thread(db, payload, match)
    message = InboundMessage(
        dedupe_key=dedupe_key,
        thread_id=thread.id if thread else None,
        lead_id=match.lead_id,
        draft_id=match.draft_id,
        delivery_id=match.delivery_id,
        provider=payload.provider,
        provider_mailbox=payload.provider_mailbox,
        provider_message_id=payload.provider_message_id,
        message_id=_normalize_message_id(payload.message_id),
        in_reply_to=_normalize_message_id(payload.in_reply_to),
        references_raw=payload.references_raw,
        from_email=_normalize_email(payload.from_email),
        from_name=payload.from_name,
        to_email=payload.to_email,
        subject=payload.subject,
        body_text=payload.body_text,
        body_snippet=payload.body_snippet,
        received_at=payload.received_at,
        raw_metadata_json=payload.raw_metadata,
        classification_status=InboundMailClassificationStatus.PENDING.value,
        classification_label=None,
        summary=None,
        confidence=None,
        next_action_suggestion=None,
        should_escalate_reviewer=False,
        classification_error=None,
        classification_role=None,
        classification_model=None,
        classified_at=None,
    )
    db.add(message)
    db.flush()

    if payload.received_at and (
        thread.last_message_at is None or payload.received_at > thread.last_message_at
    ):
        thread.last_message_at = payload.received_at

    if match.delivery_id:
        db.add(
            OutreachLog(
                lead_id=match.lead_id,
                draft_id=match.draft_id,
                action=LogAction.REPLIED,
                actor="system",
                detail=_build_reply_log_detail(payload),
            )
        )

    db.commit()
    db.refresh(message)
    db.refresh(thread)

    logger.info(
        "inbound_message_persisted",
        inbound_message_id=str(message.id),
        thread_id=str(thread.id),
        lead_id=str(message.lead_id) if message.lead_id else None,
        draft_id=str(message.draft_id) if message.draft_id else None,
        delivery_id=str(message.delivery_id) if message.delivery_id else None,
        matched_via=thread.matched_via,
        match_confidence=thread.match_confidence,
        classification_status=message.classification_status,
    )
    return message, "matched" if match.delivery else "unmatched"


def _resolve_thread(db: Session, payload: InboundMailMessage, match: DeliveryMatch) -> EmailThread:
    external_thread_id = _resolve_external_thread_id(payload)
    thread_key = _build_thread_key(payload, match, external_thread_id)

    stmt = select(EmailThread).where(
        EmailThread.provider == payload.provider,
        EmailThread.provider_mailbox == payload.provider_mailbox,
        EmailThread.thread_key == thread_key,
    )
    thread = db.execute(stmt).scalars().first()
    if thread:
        _merge_thread_match(thread, payload, match, external_thread_id)
        db.flush()
        return thread

    thread = EmailThread(
        lead_id=match.lead_id,
        draft_id=match.draft_id,
        delivery_id=match.delivery_id,
        provider=payload.provider,
        provider_mailbox=payload.provider_mailbox,
        external_thread_id=external_thread_id,
        thread_key=thread_key,
        matched_via=match.matched_via,
        match_confidence=match.match_confidence,
        last_message_at=payload.received_at,
    )
    db.add(thread)
    db.flush()
    return thread


def _merge_thread_match(
    thread: EmailThread,
    payload: InboundMailMessage,
    match: DeliveryMatch,
    external_thread_id: str | None,
) -> None:
    if external_thread_id and not thread.external_thread_id:
        thread.external_thread_id = external_thread_id
    if payload.received_at and (thread.last_message_at is None or payload.received_at > thread.last_message_at):
        thread.last_message_at = payload.received_at
    if match.delivery and (
        thread.match_confidence is None or match.match_confidence >= thread.match_confidence
    ):
        thread.lead_id = match.lead_id
        thread.draft_id = match.draft_id
        thread.delivery_id = match.delivery_id
        thread.matched_via = match.matched_via
        thread.match_confidence = match.match_confidence


def _match_delivery(db: Session, payload: InboundMailMessage) -> DeliveryMatch:
    in_reply_to = _normalize_message_id(payload.in_reply_to)
    references = _extract_reference_ids(payload.references_raw)

    direct_candidates = [candidate for candidate in [in_reply_to] if candidate]
    if direct_candidates:
        delivery = _find_delivery_by_message_ids(db, direct_candidates)
        if delivery:
            return DeliveryMatch(delivery=delivery, matched_via="message_id", match_confidence=1.0)

    if references:
        delivery = _find_delivery_by_message_ids(db, references)
        if delivery:
            return DeliveryMatch(delivery=delivery, matched_via="references", match_confidence=0.9)

    fallback_delivery = _find_delivery_by_subject_fallback(db, payload)
    if fallback_delivery:
        return DeliveryMatch(
            delivery=fallback_delivery,
            matched_via="subject_fallback",
            match_confidence=0.55,
        )

    return DeliveryMatch(delivery=None, matched_via="unmatched", match_confidence=0.0)


def _find_delivery_by_message_ids(
    db: Session, message_ids: list[str]
) -> OutreachDelivery | None:
    normalized_ids = [message_id for message_id in message_ids if message_id]
    if not normalized_ids:
        return None
    stmt = (
        select(OutreachDelivery)
        .where(
            OutreachDelivery.provider_message_id.is_not(None),
            OutreachDelivery.provider_message_id.in_(normalized_ids),
        )
        .order_by(OutreachDelivery.sent_at.desc(), OutreachDelivery.created_at.desc())
    )
    deliveries = list(db.execute(stmt).scalars().all())
    if not deliveries:
        return None
    by_message_id = {
        _normalize_message_id(delivery.provider_message_id): delivery for delivery in deliveries
    }
    for candidate in normalized_ids:
        delivery = by_message_id.get(candidate)
        if delivery:
            return delivery
    return None


def _find_delivery_by_subject_fallback(
    db: Session, payload: InboundMailMessage
) -> OutreachDelivery | None:
    from_email = _normalize_email(payload.from_email)
    normalized_subject = _normalize_subject(payload.subject)
    if not from_email or not normalized_subject:
        return None

    stmt = (
        select(OutreachDelivery)
        .where(
            OutreachDelivery.recipient_email == from_email,
            OutreachDelivery.status == OutreachDeliveryStatus.SENT,
        )
        .options(selectinload(OutreachDelivery.draft))
        .order_by(OutreachDelivery.sent_at.desc(), OutreachDelivery.created_at.desc())
        .limit(25)
    )
    deliveries = list(db.execute(stmt).scalars().all())
    for delivery in deliveries:
        if _normalize_subject(delivery.subject_snapshot) == normalized_subject:
            return delivery
    return None


def _build_reply_log_detail(payload: InboundMailMessage) -> str:
    sender = _normalize_email(payload.from_email) or "contacto desconocido"
    snippet = payload.body_snippet or payload.subject or "Respuesta recibida"
    return f"Reply recibida de {sender} — {snippet}"


def _build_thread_key(
    payload: InboundMailMessage, match: DeliveryMatch, external_thread_id: str | None
) -> str:
    if match.delivery_id:
        return f"delivery:{match.delivery_id}"
    if external_thread_id:
        return f"message:{external_thread_id}"
    normalized_subject = _normalize_subject(payload.subject)
    from_email = _normalize_email(payload.from_email)
    if from_email and normalized_subject:
        return f"subject:{from_email}:{normalized_subject}"
    return f"unmatched:{_build_dedupe_key(payload)}"


def _resolve_external_thread_id(payload: InboundMailMessage) -> str | None:
    return (
        _normalize_message_id(payload.in_reply_to)
        or (_extract_reference_ids(payload.references_raw)[0] if _extract_reference_ids(payload.references_raw) else None)
        or _normalize_message_id(payload.message_id)
        or payload.provider_message_id
    )


def _build_dedupe_key(payload: InboundMailMessage) -> str:
    provider = payload.provider.lower()
    mailbox = payload.provider_mailbox.lower()
    if payload.provider_message_id:
        return f"{provider}:{mailbox}:provider:{payload.provider_message_id}"

    message_id = _normalize_message_id(payload.message_id)
    if message_id:
        return f"{provider}:{mailbox}:message:{message_id}"

    digest_source = "|".join(
        [
            provider,
            mailbox,
            _normalize_email(payload.from_email) or "",
            _normalize_subject(payload.subject) or "",
            payload.received_at.isoformat() if payload.received_at else "",
            (payload.body_snippet or payload.body_text or "")[:160],
        ]
    )
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()
    return f"{provider}:{mailbox}:fallback:{digest}"


def _extract_reference_ids(raw_references: str | None) -> list[str]:
    if not raw_references:
        return []
    matches = [match.strip() for match in MESSAGE_ID_RE.findall(raw_references)]
    if matches:
        return [_normalize_message_id(match) for match in matches if _normalize_message_id(match)]
    return [
        _normalize_message_id(token)
        for token in raw_references.split()
        if _normalize_message_id(token)
    ]


def _normalize_message_id(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1]
    normalized = normalized.strip()
    return normalized or None


def _normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_subject(value: str | None) -> str | None:
    if not value:
        return None
    normalized = SUBJECT_PREFIX_RE.sub("", value.strip())
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized or None
