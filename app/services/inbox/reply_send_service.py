from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.logging import get_logger
from app.mail.provider import MailProviderError
from app.models.inbound_mail import InboundMessage
from app.models.outreach import LogAction, OutreachLog
from app.models.reply_assistant import ReplyAssistantDraft, ReplyAssistantReviewStatus
from app.models.reply_assistant_send import ReplyAssistantSend, ReplyAssistantSendStatus
from app.schemas.reply_send import ReplyAssistantSendStatusResponse
from app.services.inbox.inbound_mail_service import _normalize_message_id as normalize_inbound_message_id
from app.services.outreach.mail_service import (
    DraftRecipientMissingError,
    build_mail_send_request,
    ensure_outbound_mail_ready,
    send_mail,
)

logger = get_logger(__name__)


class ReplySendServiceError(RuntimeError):
    """Base error for manual reply sending."""


class ReplyDraftNotFoundError(ReplySendServiceError):
    """Raised when the reply draft does not exist."""


class ReplyDraftValidationError(ReplySendServiceError):
    """Raised when a reply draft is not ready to send."""


class ReplyDraftAlreadySentError(ReplySendServiceError):
    """Raised when the reply draft already has a successful send."""


class ReplyDraftAlreadySendingError(ReplySendServiceError):
    """Raised when a send is already in progress."""


def get_reply_assistant_draft_for_message(
    db: Session, message_id: uuid.UUID
) -> ReplyAssistantDraft | None:
    stmt = (
        select(ReplyAssistantDraft)
        .execution_options(populate_existing=True)
        .options(
            joinedload(ReplyAssistantDraft.inbound_message).joinedload(InboundMessage.thread),
            joinedload(ReplyAssistantDraft.inbound_message).joinedload(InboundMessage.lead),
            joinedload(ReplyAssistantDraft.review),
            selectinload(ReplyAssistantDraft.sends),
        )
        .where(ReplyAssistantDraft.inbound_message_id == message_id)
    )
    draft = db.execute(stmt).scalars().first()
    if draft:
        _attach_send_metadata(draft)
    return draft


def update_reply_assistant_draft(
    db: Session,
    message_id: uuid.UUID,
    *,
    subject: str | None = None,
    body: str | None = None,
    edited_by: str | None = None,
) -> ReplyAssistantDraft:
    draft = get_reply_assistant_draft_for_message(db, message_id)
    if not draft:
        raise ReplyDraftNotFoundError("Reply assistant draft not found.")

    did_edit = False
    if subject is not None:
        draft.subject = subject
        did_edit = True
    if body is not None:
        draft.body = body
        did_edit = True

    if did_edit:
        draft.edited_at = datetime.now(UTC)
        draft.edited_by = (edited_by or "user").strip() or "user"
        db.commit()
        db.refresh(draft)

    _attach_send_metadata(draft)
    logger.info(
        "reply_assistant_draft_updated",
        draft_id=str(draft.id),
        inbound_message_id=str(draft.inbound_message_id),
        edited_by=draft.edited_by,
        did_edit=did_edit,
    )
    return draft


def get_reply_send_status(db: Session, message_id: uuid.UUID) -> ReplyAssistantSendStatusResponse:
    draft = get_reply_assistant_draft_for_message(db, message_id)
    if not draft:
        raise ReplyDraftNotFoundError("Reply assistant draft not found.")

    return ReplyAssistantSendStatusResponse(
        draft_id=draft.id,
        inbound_message_id=draft.inbound_message_id,
        review_is_stale=draft.review_is_stale,
        send_blocked_reason=draft.send_blocked_reason,
        latest_send=draft.latest_send,
        sent=bool(draft.latest_send and draft.latest_send.status == ReplyAssistantSendStatus.SENT),
    )


def send_reply_assistant_draft(db: Session, message_id: uuid.UUID) -> ReplyAssistantSend:
    draft = get_reply_assistant_draft_for_message(db, message_id)
    if not draft:
        raise ReplyDraftNotFoundError("Reply assistant draft not found.")

    blocked_reason = draft.send_blocked_reason
    latest_send = draft.latest_send
    if latest_send and latest_send.status == ReplyAssistantSendStatus.SENT:
        raise ReplyDraftAlreadySentError(blocked_reason or "Reply draft has already been sent.")
    if latest_send and latest_send.status == ReplyAssistantSendStatus.SENDING:
        # Auto-recover stuck SENDING after 5 minutes
        from datetime import timedelta
        if latest_send.created_at and (datetime.now(UTC) - latest_send.created_at) > timedelta(minutes=5):
            latest_send.status = ReplyAssistantSendStatus.FAILED
            latest_send.error = "Send timed out after 5 minutes."
            db.commit()
            db.refresh(latest_send)
        else:
            raise ReplyDraftAlreadySendingError(blocked_reason or "Reply draft is already being sent.")
    if blocked_reason:
        raise ReplyDraftValidationError(blocked_reason)

    config = ensure_outbound_mail_ready(db)
    inbound_message = draft.inbound_message
    recipient_email = _require_recipient_email(inbound_message)
    subject = _require_subject(draft, inbound_message)
    body = _require_body(draft)
    in_reply_to = _normalize_message_id(inbound_message.message_id if inbound_message else None)
    references_raw = _build_references_raw(
        inbound_message.references_raw if inbound_message else None,
        inbound_message.message_id if inbound_message else None,
    )

    send_record = ReplyAssistantSend(
        reply_assistant_draft_id=draft.id,
        inbound_message_id=draft.inbound_message_id,
        thread_id=draft.thread_id,
        lead_id=draft.lead_id,
        status=ReplyAssistantSendStatus.SENDING,
        provider=config.provider,
        recipient_email=recipient_email,
        from_email_snapshot=config.from_email,
        reply_to_snapshot=config.reply_to,
        subject_snapshot=subject,
        body_snapshot=body,
        in_reply_to=in_reply_to,
        references_raw=references_raw,
    )
    db.add(send_record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        refreshed = get_reply_assistant_draft_for_message(db, message_id)
        latest = refreshed.latest_send if refreshed else None
        if latest and latest.status == ReplyAssistantSendStatus.SENT:
            raise ReplyDraftAlreadySentError("Reply draft has already been sent.") from exc
        if latest and latest.status == ReplyAssistantSendStatus.SENDING:
            raise ReplyDraftAlreadySendingError("Reply draft is already being sent.") from exc
        raise

    db.refresh(send_record)

    request = build_mail_send_request(
        config=config,
        recipient_email=send_record.recipient_email,
        subject=send_record.subject_snapshot,
        body=send_record.body_snapshot,
        in_reply_to=send_record.in_reply_to,
        references_raw=send_record.references_raw,
    )
    try:
        result = send_mail(request)
    except MailProviderError as exc:
        send_record.status = ReplyAssistantSendStatus.FAILED
        send_record.error = str(exc)
        db.commit()
        db.refresh(send_record)
        try:
            from app.services.notifications.notification_emitter import on_send_failed
            on_send_failed(db, send_id=send_record.id, recipient=send_record.recipient_email, error=send_record.error, send_type="reply_assistant")
        except Exception:
            pass
        logger.warning(
            "reply_assistant_send_failed",
            send_id=str(send_record.id),
            draft_id=str(draft.id),
            inbound_message_id=str(draft.inbound_message_id),
            error=send_record.error,
        )
        return send_record

    send_record.status = ReplyAssistantSendStatus.SENT
    send_record.provider = result.provider
    send_record.provider_message_id = result.provider_message_id
    send_record.sent_at = result.sent_at
    send_record.error = None
    if draft.lead_id is not None:
        db.add(
            OutreachLog(
                lead_id=draft.lead_id,
                draft_id=None,
                action=LogAction.SENT,
                actor="user",
                detail=f"Reply manual enviada a {send_record.recipient_email}",
            )
        )
    db.commit()
    db.refresh(send_record)
    logger.info(
        "reply_assistant_send_sent",
        send_id=str(send_record.id),
        draft_id=str(draft.id),
        inbound_message_id=str(draft.inbound_message_id),
        provider_message_id=send_record.provider_message_id,
        recipient_email=send_record.recipient_email,
    )
    return send_record


def _attach_send_metadata(draft: ReplyAssistantDraft) -> None:
    setattr(draft, "_send_blocked_reason", _compute_send_blocked_reason(draft))


def attach_reply_send_metadata(draft: ReplyAssistantDraft | None) -> ReplyAssistantDraft | None:
    if draft is None:
        return None
    _attach_send_metadata(draft)
    return draft


def _compute_send_blocked_reason(draft: ReplyAssistantDraft) -> str | None:
    inbound_message = draft.inbound_message
    if inbound_message is None:
        return "Reply draft is missing inbound context."

    latest_send = draft.latest_send
    if latest_send and latest_send.status == ReplyAssistantSendStatus.SENT:
        return "Reply draft has already been sent."
    if latest_send and latest_send.status == ReplyAssistantSendStatus.SENDING:
        # Auto-recover stuck SENDING after 5 minutes
        from datetime import timedelta
        if latest_send.created_at and (datetime.now(UTC) - latest_send.created_at) > timedelta(minutes=5):
            latest_send.status = ReplyAssistantSendStatus.FAILED
            latest_send.error = "Send timed out after 5 minutes."
        else:
            return "Reply draft is already being sent."

    review = draft.review
    if review and review.status == ReplyAssistantReviewStatus.PENDING:
        return "Reply draft review is still pending."
    if review and review.should_edit and review.reviewed_at:
        if draft.edited_at is None or draft.edited_at <= review.reviewed_at:
            return "Reply draft review recommends editing before sending."

    recipient_email = ((inbound_message.from_email if inbound_message else None) or "").strip()
    if not recipient_email:
        return "Inbound message does not have a sender email."

    if not _resolve_reply_subject(draft.subject, inbound_message.subject if inbound_message else None):
        return "Reply draft subject is missing."

    if not (draft.body or "").strip():
        return "Reply draft body is missing."

    return None


def _require_recipient_email(inbound_message: InboundMessage | None) -> str:
    recipient_email = ((inbound_message.from_email if inbound_message else None) or "").strip().lower()
    if not recipient_email:
        raise DraftRecipientMissingError("Inbound message does not have a sender email.")
    return recipient_email


def _require_subject(draft: ReplyAssistantDraft, inbound_message: InboundMessage | None) -> str:
    subject = _resolve_reply_subject(draft.subject, inbound_message.subject if inbound_message else None)
    if not subject:
        raise ReplyDraftValidationError("Reply draft subject is missing.")
    return subject


def _require_body(draft: ReplyAssistantDraft) -> str:
    body = (draft.body or "").strip()
    if not body:
        raise ReplyDraftValidationError("Reply draft body is missing.")
    return body


def _resolve_reply_subject(draft_subject: str | None, inbound_subject: str | None) -> str | None:
    candidate = (draft_subject or "").strip() or (inbound_subject or "").strip()
    if not candidate:
        return None
    # Strip CRLF to prevent header injection
    candidate = candidate.replace("\r", "").replace("\n", "")
    if candidate.lower().startswith("re:"):
        return candidate
    return f"Re: {candidate}"


def _normalize_message_id(value: str | None) -> str | None:
    return normalize_inbound_message_id(value)


def _build_references_raw(existing_references: str | None, message_id: str | None) -> str | None:
    tokens: list[str] = []
    for candidate in (existing_references or "").split():
        normalized = _normalize_message_id(candidate)
        if normalized and normalized not in tokens:
            tokens.append(normalized)
    normalized_message_id = _normalize_message_id(message_id)
    if normalized_message_id and normalized_message_id not in tokens:
        tokens.append(normalized_message_id)
    return " ".join(tokens) if tokens else None
