from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.logging import get_logger
from app.llm.client import generate_reply_assistant_draft as llm_generate_reply_assistant_draft
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole
from app.models.inbound_mail import InboundMessage
from app.models.outreach_delivery import OutreachDelivery
from app.models.reply_assistant import ReplyAssistantDraft, ReplyAssistantDraftStatus

logger = get_logger(__name__)


def _apply_generated_reply_draft(
    draft: ReplyAssistantDraft,
    *,
    message: InboundMessage,
    related_outbound_draft,
    generated: dict,
    role: LLMRole,
    model: str,
    should_escalate_reviewer: bool,
) -> None:
    draft.thread_id = message.thread_id
    draft.lead_id = message.lead_id
    draft.related_delivery_id = message.delivery_id
    draft.related_outbound_draft_id = related_outbound_draft.id if related_outbound_draft else None
    draft.status = ReplyAssistantDraftStatus.GENERATED
    draft.subject = generated["subject"]
    draft.body = generated["body"]
    draft.summary = generated.get("summary")
    draft.suggested_tone = generated.get("suggested_tone")
    draft.should_escalate_reviewer = should_escalate_reviewer
    draft.generator_role = role.value
    draft.generator_model = model


def get_reply_assistant_draft_for_message(
    db: Session, message_id: uuid.UUID
) -> ReplyAssistantDraft | None:
    stmt = (
        select(ReplyAssistantDraft)
        .options(
            joinedload(ReplyAssistantDraft.inbound_message),
            joinedload(ReplyAssistantDraft.thread),
            joinedload(ReplyAssistantDraft.lead),
            joinedload(ReplyAssistantDraft.related_delivery),
            joinedload(ReplyAssistantDraft.related_outbound_draft),
            joinedload(ReplyAssistantDraft.review),
        )
        .where(ReplyAssistantDraft.inbound_message_id == message_id)
    )
    return db.execute(stmt).scalars().first()


def get_inbound_message_with_reply_context(
    db: Session, message_id: uuid.UUID
) -> InboundMessage | None:
    stmt = (
        select(InboundMessage)
        .options(
            joinedload(InboundMessage.thread),
            joinedload(InboundMessage.lead),
            joinedload(InboundMessage.delivery).joinedload(OutreachDelivery.draft),
            joinedload(InboundMessage.draft),
        )
        .where(InboundMessage.id == message_id)
    )
    return db.execute(stmt).scalars().first()


def generate_reply_assistant_draft(
    db: Session, message_id: uuid.UUID
) -> ReplyAssistantDraft | None:
    message = get_inbound_message_with_reply_context(db, message_id)
    if not message:
        return None

    role = LLMRole.EXECUTOR
    model = resolve_model_for_role(role)
    existing = get_reply_assistant_draft_for_message(db, message_id)
    related_outbound_draft = message.draft or (message.delivery.draft if message.delivery else None)

    generated = llm_generate_reply_assistant_draft(
        business_name=message.lead.business_name if message.lead else None,
        industry=message.lead.industry if message.lead else None,
        city=message.lead.city if message.lead else None,
        lead_email=message.lead.email if message.lead else None,
        classification_label=message.classification_label,
        classification_summary=message.summary,
        next_action_suggestion=message.next_action_suggestion,
        should_escalate_reviewer=message.should_escalate_reviewer,
        outbound_subject=message.delivery.subject_snapshot if message.delivery else None,
        outbound_body=related_outbound_draft.body if related_outbound_draft else None,
        thread_context=_build_thread_context(message),
        from_email=message.from_email,
        to_email=message.to_email,
        subject=message.subject,
        body_text=message.body_text,
        role=role,
    )

    should_escalate_reviewer = bool(
        message.should_escalate_reviewer or generated.get("should_escalate_reviewer")
    )

    if existing:
        draft = existing
    else:
        draft = ReplyAssistantDraft(inbound_message_id=message.id)
        db.add(draft)

    if draft.review is not None:
        db.delete(draft.review)
        db.flush()

    _apply_generated_reply_draft(
        draft,
        message=message,
        related_outbound_draft=related_outbound_draft,
        generated=generated,
        role=role,
        model=model,
        should_escalate_reviewer=should_escalate_reviewer,
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        draft = get_reply_assistant_draft_for_message(db, message.id)
        if not draft:
            raise

        if draft.review is not None:
            db.delete(draft.review)
            db.flush()

        _apply_generated_reply_draft(
            draft,
            message=message,
            related_outbound_draft=related_outbound_draft,
            generated=generated,
            role=role,
            model=model,
            should_escalate_reviewer=should_escalate_reviewer,
        )
        db.commit()

    db.refresh(draft)

    logger.info(
        "reply_assistant_draft_generated",
        inbound_message_id=str(message.id),
        lead_id=str(message.lead_id) if message.lead_id else None,
        thread_id=str(message.thread_id) if message.thread_id else None,
        draft_id=str(draft.id),
        role=role.value,
        model=model,
        regenerated=existing is not None,
        should_escalate_reviewer=draft.should_escalate_reviewer,
    )
    return draft


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
