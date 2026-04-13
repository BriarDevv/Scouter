"""Inbound mail service — orchestrates sync, persistence and query operations.

Sub-module layout:
- mail_helpers      : normalisation utilities (message IDs, emails, subjects)
- message_dedup     : deduplication key builder
- thread_matcher    : delivery/thread matching logic
- classification_dispatch : auto-classification dispatch
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
from app.models.outreach import LogAction, OutreachLog
from app.models.reply_assistant import ReplyAssistantDraft
from app.services.inbox.classification_dispatch import dispatch_classification
from app.services.inbox.mail_helpers import normalize_email, normalize_message_id
from app.services.inbox.message_dedup import build_dedupe_key
from app.services.inbox.thread_matcher import (
    build_reply_log_detail,
    match_delivery,
    resolve_thread,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Backward-compatible aliases so existing callers that import private names
# from this module continue to work (notably reply_send_service).
# ---------------------------------------------------------------------------
_normalize_message_id = normalize_message_id


class InboundMailServiceError(RuntimeError):
    """Base inbound mail service error."""


class InboundMailDisabledError(InboundMailServiceError):
    """Raised when inbound sync is disabled."""


def get_inbound_provider() -> IMAPInboundMailProvider:
    if settings.MAIL_INBOUND_PROVIDER.lower() != "imap":
        raise InboundMailProviderError(
            f"Unsupported MAIL_INBOUND_PROVIDER {settings.MAIL_INBOUND_PROVIDER!r}."
        )
    return IMAPInboundMailProvider()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


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
            selectinload(InboundMessage.reply_assistant_draft).selectinload(
                ReplyAssistantDraft.review
            ),
            selectinload(InboundMessage.reply_assistant_draft).selectinload(
                ReplyAssistantDraft.sends
            ),
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
            selectinload(InboundMessage.reply_assistant_draft).selectinload(
                ReplyAssistantDraft.review
            ),
            selectinload(InboundMessage.reply_assistant_draft).selectinload(
                ReplyAssistantDraft.sends
            ),
        )
        .where(InboundMessage.id == message_id)
    )
    return db.execute(stmt).scalars().first()


def list_email_threads(
    db: Session, *, lead_id: uuid.UUID | None = None, limit: int = 50
) -> list[EmailThread]:
    stmt = (
        select(EmailThread)
        .options(
            selectinload(EmailThread.messages)
            .selectinload(InboundMessage.reply_assistant_draft)
            .selectinload(ReplyAssistantDraft.review),
            selectinload(EmailThread.messages)
            .selectinload(InboundMessage.reply_assistant_draft)
            .selectinload(ReplyAssistantDraft.sends),
        )
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
            selectinload(EmailThread.messages)
            .selectinload(InboundMessage.reply_assistant_draft)
            .selectinload(ReplyAssistantDraft.review),
            selectinload(EmailThread.messages)
            .selectinload(InboundMessage.reply_assistant_draft)
            .selectinload(ReplyAssistantDraft.sends),
        )
        .where(EmailThread.id == thread_id)
    )
    return db.execute(stmt).scalars().first()


def get_inbound_sync_status(db: Session) -> InboundMailSyncRun | None:
    stmt = select(InboundMailSyncRun).order_by(InboundMailSyncRun.started_at.desc()).limit(1)
    return db.execute(stmt).scalars().first()


# ---------------------------------------------------------------------------
# Sync orchestration
# ---------------------------------------------------------------------------


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
    db.flush()
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

            if persisted_message:
                dispatch_classification(db, persisted_message)

        sync_run.status = InboundMailSyncStatus.COMPLETED.value
        sync_run.error = None
        sync_run.completed_at = datetime.now(UTC)
        db.flush()
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
        db.flush()
        db.refresh(sync_run)
        try:
            from app.services.notifications.notification_emitter import on_sync_failed

            on_sync_failed(db, sync_run_id=sync_run.id, error=sync_run.error)
        except Exception:
            logger.debug("inbound_sync_failed_notification_failed", exc_info=True)
        logger.warning(
            "inbound_mail_sync_failed",
            sync_run_id=str(sync_run.id),
            error=sync_run.error,
        )
        raise


def _persist_inbound_message(
    db: Session, payload: InboundMailMessage
) -> tuple[InboundMessage | None, str]:
    dedupe_key = build_dedupe_key(payload)
    existing = (
        db.execute(select(InboundMessage).where(InboundMessage.dedupe_key == dedupe_key))
        .scalars()
        .first()
    )
    if existing:
        return None, "deduplicated"

    match = match_delivery(db, payload)
    thread = resolve_thread(db, payload, match)
    message = InboundMessage(
        dedupe_key=dedupe_key,
        thread_id=thread.id if thread else None,
        lead_id=match.lead_id,
        draft_id=match.draft_id,
        delivery_id=match.delivery_id,
        provider=payload.provider,
        provider_mailbox=payload.provider_mailbox,
        provider_message_id=payload.provider_message_id,
        message_id=normalize_message_id(payload.message_id),
        in_reply_to=normalize_message_id(payload.in_reply_to),
        references_raw=payload.references_raw,
        from_email=normalize_email(payload.from_email),
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
                detail=build_reply_log_detail(payload),
            )
        )

    # Auto-advance lead from CONTACTED to REPLIED on inbound match
    if match.lead_id and match.delivery_id:
        from app.models.lead import Lead, LeadStatus

        lead = db.get(Lead, match.lead_id)
        if lead and lead.status == LeadStatus.CONTACTED:
            lead.status = LeadStatus.REPLIED
            logger.info(
                "lead_auto_advanced_to_replied",
                lead_id=str(lead.id),
                delivery_id=str(match.delivery_id),
            )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info("inbound_message_deduplicated_on_commit", dedupe_key=dedupe_key)
        return None, "deduplicated"
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
    return message, "matched" if (match.delivery or match.reply_send) else "unmatched"
