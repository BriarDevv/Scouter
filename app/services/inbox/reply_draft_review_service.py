from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.llm.client import review_reply_assistant_draft as llm_review_reply_assistant_draft
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole
from app.models.inbound_mail import InboundMessage
from app.models.outreach_delivery import OutreachDelivery
from app.models.reply_assistant import (
    ReplyAssistantDraft,
    ReplyAssistantReview,
    ReplyAssistantReviewStatus,
)
from app.services.inbox.reply_send_service import attach_reply_send_metadata

logger = get_logger(__name__)


def get_reply_assistant_review_for_message(
    db: Session, message_id: uuid.UUID
) -> ReplyAssistantReview | None:
    stmt = (
        select(ReplyAssistantReview)
        .execution_options(populate_existing=True)
        .options(joinedload(ReplyAssistantReview.draft))
        .where(ReplyAssistantReview.inbound_message_id == message_id)
    )
    return db.execute(stmt).scalars().first()


def get_inbound_message_with_review_context(
    db: Session, message_id: uuid.UUID
) -> InboundMessage | None:
    stmt = (
        select(InboundMessage)
        .execution_options(populate_existing=True)
        .options(
            joinedload(InboundMessage.thread),
            joinedload(InboundMessage.lead),
            joinedload(InboundMessage.delivery).joinedload(OutreachDelivery.draft),
            joinedload(InboundMessage.draft),
            joinedload(InboundMessage.reply_assistant_draft).joinedload(ReplyAssistantDraft.review),
        )
        .where(InboundMessage.id == message_id)
    )
    return db.execute(stmt).scalars().first()


def ensure_reply_assistant_review_pending(
    db: Session,
    message_id: uuid.UUID,
    *,
    task_id: str | None = None,
) -> ReplyAssistantReview | None:
    message = get_inbound_message_with_review_context(db, message_id)
    if not message or not message.reply_assistant_draft:
        return None

    existing = message.reply_assistant_draft.review
    if existing:
        review = existing
    else:
        review = ReplyAssistantReview(
            reply_assistant_draft_id=message.reply_assistant_draft.id,
            inbound_message_id=message.id,
            thread_id=message.thread_id,
            lead_id=message.lead_id,
        )
        db.add(review)

    review.thread_id = message.thread_id
    review.lead_id = message.lead_id
    review.status = ReplyAssistantReviewStatus.PENDING
    review.summary = None
    review.feedback = None
    review.suggested_edits = None
    review.recommended_action = None
    review.should_use_as_is = False
    review.should_edit = True
    review.should_escalate = False
    review.reviewer_role = None
    review.reviewer_model = None
    review.task_id = task_id
    review.error = None
    review.reviewed_at = None

    db.flush()
    db.refresh(review)
    return review


def review_reply_assistant_draft_with_reviewer(
    db: Session, message_id: uuid.UUID
) -> dict | None:
    from app.services.settings.operational_settings_service import get_cached_settings

    ops = get_cached_settings(db)
    if not ops.allow_reply_assistant_generation:
        logger.info("reply_assistant_review_disabled_by_settings", message_id=str(message_id))
        return None

    message = get_inbound_message_with_review_context(db, message_id)
    if not message or not message.reply_assistant_draft:
        return None

    role = LLMRole.REVIEWER
    model = resolve_model_for_role(role)
    draft = message.reply_assistant_draft
    related_outbound_draft = message.draft or (message.delivery.draft if message.delivery else None)

    review = draft.review or ensure_reply_assistant_review_pending(db, message.id)
    if not review:
        return None

    result = llm_review_reply_assistant_draft(
        business_name=message.lead.business_name if message.lead else None,
        industry=message.lead.industry if message.lead else None,
        city=message.lead.city if message.lead else None,
        lead_email=message.lead.email if message.lead else None,
        classification_label=message.classification_label,
        classification_summary=message.summary,
        next_action_suggestion=message.next_action_suggestion,
        reply_should_escalate_reviewer=message.should_escalate_reviewer or draft.should_escalate_reviewer,
        outbound_subject=message.delivery.subject_snapshot if message.delivery else None,
        outbound_body=related_outbound_draft.body if related_outbound_draft else None,
        thread_context=_build_thread_context(message),
        from_email=message.from_email,
        to_email=message.to_email,
        subject=message.subject,
        body_text=message.body_text,
        draft_subject=draft.subject,
        draft_body=draft.body,
        draft_summary=draft.summary,
        suggested_tone=draft.suggested_tone,
        role=role,
    )

    review.status = ReplyAssistantReviewStatus.REVIEWED
    review.summary = result.get("summary")
    review.feedback = result.get("feedback")
    review.suggested_edits = result.get("suggested_edits") or []
    review.recommended_action = result.get("recommended_action")
    review.should_use_as_is = bool(result.get("should_use_as_is"))
    review.should_edit = bool(result.get("should_edit"))
    review.should_escalate = bool(result.get("should_escalate"))
    review.reviewer_role = role.value
    review.reviewer_model = model
    review.error = None
    review.reviewed_at = datetime.now(UTC)

    db.flush()
    db.refresh(review)
    attach_reply_send_metadata(draft)

    payload = {
        "review_id": review.id,
        "reply_assistant_draft_id": draft.id,
        "inbound_message_id": message.id,
        "lead_id": message.lead_id,
        "thread_id": message.thread_id,
        "role": role,
        "model": model,
        "status": review.status,
        "summary": review.summary,
        "feedback": review.feedback,
        "suggested_edits": review.suggested_edits or [],
        "recommended_action": review.recommended_action,
        "should_use_as_is": review.should_use_as_is,
        "should_edit": review.should_edit,
        "should_escalate": review.should_escalate,
        "reviewed_at": review.reviewed_at,
    }
    logger.info(
        "reply_assistant_draft_review_completed",
        inbound_message_id=str(message.id),
        reply_assistant_draft_id=str(draft.id),
        review_id=str(review.id),
        role=role.value,
        model=model,
        recommended_action=review.recommended_action,
    )
    return payload


def mark_reply_assistant_review_failed(
    db: Session,
    message_id: uuid.UUID,
    *,
    error: str,
    task_id: str | None = None,
) -> ReplyAssistantReview | None:
    message = get_inbound_message_with_review_context(db, message_id)
    if not message or not message.reply_assistant_draft:
        return None

    review = message.reply_assistant_draft.review or ensure_reply_assistant_review_pending(
        db, message.id, task_id=task_id
    )
    if not review:
        return None

    review.status = ReplyAssistantReviewStatus.FAILED
    review.error = error
    review.task_id = task_id or review.task_id
    review.reviewed_at = None
    db.flush()
    db.refresh(review)
    return review


def _build_thread_context(message: InboundMessage) -> str:
    thread = message.thread
    if not thread or not thread.messages:
        return "No previous thread context available"

    ordered_messages = sorted(
        thread.messages,
        key=lambda item: item.received_at.isoformat() if item.received_at else item.created_at.isoformat(),
    )
    context_lines: list[str] = []
    for item in ordered_messages[-3:]:
        if item.id == message.id:
            continue
        sender = item.from_email or "unknown"
        snippet = item.body_snippet or item.body_text or ""
        cleaned = " ".join(snippet.split())[:280]
        if cleaned:
            context_lines.append(f"- {sender}: {cleaned}")

    return "\n".join(context_lines) if context_lines else "No previous thread context available"
