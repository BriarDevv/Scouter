"""Thread matching — correlate inbound messages to outreach deliveries and reply sends."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.mail.inbound_provider import InboundMailMessage
from app.models.inbound_mail import EmailThread
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus
from app.models.reply_assistant_send import ReplyAssistantSend, ReplyAssistantSendStatus
from app.services.inbox.mail_helpers import (
    SUBJECT_PREFIX_RE,
    extract_reference_ids,
    normalize_email,
    normalize_message_id,
    normalize_subject,
)
from app.services.inbox.message_dedup import build_dedupe_key


@dataclass(frozen=True)
class DeliveryMatch:
    delivery: OutreachDelivery | None
    matched_via: str
    match_confidence: float
    reply_send: ReplyAssistantSend | None = None

    @property
    def lead_id(self) -> uuid.UUID | None:
        if self.delivery:
            return self.delivery.lead_id
        return self.reply_send.lead_id if self.reply_send else None

    @property
    def draft_id(self) -> uuid.UUID | None:
        return self.delivery.draft_id if self.delivery else None

    @property
    def delivery_id(self) -> uuid.UUID | None:
        return self.delivery.id if self.delivery else None

    @property
    def thread_id(self) -> uuid.UUID | None:
        return self.reply_send.thread_id if self.reply_send else None


def match_delivery(db: Session, payload: InboundMailMessage) -> DeliveryMatch:
    in_reply_to = normalize_message_id(payload.in_reply_to)
    references = extract_reference_ids(payload.references_raw)

    direct_candidates = [candidate for candidate in [in_reply_to] if candidate]
    if direct_candidates:
        delivery = _find_delivery_by_message_ids(db, direct_candidates)
        if delivery:
            return DeliveryMatch(delivery=delivery, matched_via="message_id", match_confidence=1.0)
        reply_send = _find_reply_send_by_message_ids(db, direct_candidates)
        if reply_send:
            return DeliveryMatch(
                delivery=None,
                reply_send=reply_send,
                matched_via="message_id",
                match_confidence=1.0,
            )

    if references:
        delivery = _find_delivery_by_message_ids(db, references)
        if delivery:
            return DeliveryMatch(delivery=delivery, matched_via="references", match_confidence=0.9)
        reply_send = _find_reply_send_by_message_ids(db, references)
        if reply_send:
            return DeliveryMatch(
                delivery=None,
                reply_send=reply_send,
                matched_via="references",
                match_confidence=0.9,
            )

    fallback_delivery = _find_delivery_by_subject_fallback(db, payload)
    if fallback_delivery:
        return DeliveryMatch(
            delivery=fallback_delivery,
            matched_via="subject_fallback",
            match_confidence=0.3,
        )

    return DeliveryMatch(
        delivery=None, reply_send=None, matched_via="unmatched", match_confidence=0.0
    )


def resolve_thread(db: Session, payload: InboundMailMessage, match: DeliveryMatch) -> EmailThread:
    if match.thread_id:
        thread = db.get(EmailThread, match.thread_id)
        if thread:
            _merge_thread_match(thread, payload, match, _resolve_external_thread_id(payload))
            db.flush()
            return thread

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


def build_reply_log_detail(payload: InboundMailMessage) -> str:
    sender = normalize_email(payload.from_email) or "contacto desconocido"
    snippet = payload.body_snippet or payload.subject or "Respuesta recibida"
    return f"Reply recibida de {sender} \u2014 {snippet}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_delivery_by_message_ids(db: Session, message_ids: list[str]) -> OutreachDelivery | None:
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
        normalize_message_id(delivery.provider_message_id): delivery for delivery in deliveries
    }
    for candidate in normalized_ids:
        delivery = by_message_id.get(candidate)
        if delivery:
            return delivery
    return None


def _find_reply_send_by_message_ids(
    db: Session, message_ids: list[str]
) -> ReplyAssistantSend | None:
    normalized_ids = [message_id for message_id in message_ids if message_id]
    if not normalized_ids:
        return None
    stmt = (
        select(ReplyAssistantSend)
        .where(
            ReplyAssistantSend.provider_message_id.is_not(None),
            ReplyAssistantSend.provider_message_id.in_(normalized_ids),
            ReplyAssistantSend.status == ReplyAssistantSendStatus.SENT,
        )
        .order_by(ReplyAssistantSend.sent_at.desc(), ReplyAssistantSend.created_at.desc())
    )
    sends = list(db.execute(stmt).scalars().all())
    if not sends:
        return None
    by_message_id = {normalize_message_id(send.provider_message_id): send for send in sends}
    for candidate in normalized_ids:
        reply_send = by_message_id.get(candidate)
        if reply_send:
            return reply_send
    return None


def _find_delivery_by_subject_fallback(
    db: Session, payload: InboundMailMessage
) -> OutreachDelivery | None:
    from_email = normalize_email(payload.from_email)
    raw_subject = (payload.subject or "").strip()
    normalized_subj = normalize_subject(payload.subject)
    if not from_email or not normalized_subj:
        return None

    # CC-8: Require the inbound subject starts with a reply prefix (Re:/Fwd:)
    if not SUBJECT_PREFIX_RE.search(raw_subject):
        return None

    stmt = (
        select(OutreachDelivery)
        .where(
            OutreachDelivery.recipient_email == from_email,
            OutreachDelivery.status == OutreachDeliveryStatus.SENT,
            OutreachDelivery.sent_at >= (datetime.now(UTC) - timedelta(days=30)),
        )
        .options(selectinload(OutreachDelivery.draft))
        .order_by(
            OutreachDelivery.sent_at.desc(),
            OutreachDelivery.created_at.desc(),
        )
        .limit(10)
    )
    deliveries = list(db.execute(stmt).scalars().all())
    for delivery in deliveries:
        if normalize_subject(delivery.subject_snapshot) == normalized_subj:
            return delivery
    return None


def _merge_thread_match(
    thread: EmailThread,
    payload: InboundMailMessage,
    match: DeliveryMatch,
    external_thread_id: str | None,
) -> None:
    if external_thread_id and not thread.external_thread_id:
        thread.external_thread_id = external_thread_id
    if payload.received_at and (
        thread.last_message_at is None or payload.received_at > thread.last_message_at
    ):
        thread.last_message_at = payload.received_at
    if match.delivery and (
        thread.match_confidence is None or match.match_confidence >= thread.match_confidence
    ):
        thread.lead_id = match.lead_id
        thread.draft_id = match.draft_id
        thread.delivery_id = match.delivery_id
        thread.matched_via = match.matched_via
        thread.match_confidence = match.match_confidence
    elif match.reply_send and (
        thread.match_confidence is None or match.match_confidence >= thread.match_confidence
    ):
        thread.lead_id = match.lead_id
        thread.matched_via = match.matched_via
        thread.match_confidence = match.match_confidence


def _build_thread_key(
    payload: InboundMailMessage, match: DeliveryMatch, external_thread_id: str | None
) -> str:
    if match.delivery_id:
        return f"delivery:{match.delivery_id}"
    if external_thread_id:
        return f"message:{external_thread_id}"
    normalized_subj = normalize_subject(payload.subject)
    from_email = normalize_email(payload.from_email)
    if from_email and normalized_subj:
        month_bucket = payload.received_at.strftime("%Y-%m") if payload.received_at else "unknown"
        return f"subject:{from_email}:{normalized_subj}:{month_bucket}"
    return f"unmatched:{build_dedupe_key(payload)}"


def _resolve_external_thread_id(payload: InboundMailMessage) -> str | None:
    return (
        normalize_message_id(payload.in_reply_to)
        or (
            extract_reference_ids(payload.references_raw)[0]
            if extract_reference_ids(payload.references_raw)
            else None
        )
        or normalize_message_id(payload.message_id)
        or payload.provider_message_id
    )
