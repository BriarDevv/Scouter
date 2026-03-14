from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.client import LLMError, classify_inbound_reply as llm_classify_inbound_reply
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole
from app.models.inbound_mail import InboundMailClassificationStatus, InboundMessage

logger = get_logger(__name__)

VALID_REPLY_LABELS = {
    "interested",
    "not_interested",
    "neutral",
    "asked_for_quote",
    "asked_for_meeting",
    "asked_for_more_info",
    "wrong_contact",
    "out_of_office",
    "spam_or_irrelevant",
    "needs_human_review",
}


class ReplyClassificationError(RuntimeError):
    """Raised when an inbound reply cannot be classified correctly."""


def get_inbound_message_for_classification(
    db: Session, message_id: uuid.UUID
) -> InboundMessage | None:
    stmt = (
        select(InboundMessage)
        .options(
            joinedload(InboundMessage.lead),
            joinedload(InboundMessage.draft),
            joinedload(InboundMessage.delivery),
        )
        .where(InboundMessage.id == message_id)
    )
    return db.execute(stmt).scalars().first()


def list_pending_inbound_messages(db: Session, *, limit: int = 25) -> list[InboundMessage]:
    stmt = (
        select(InboundMessage)
        .options(
            joinedload(InboundMessage.lead),
            joinedload(InboundMessage.draft),
            joinedload(InboundMessage.delivery),
        )
        .where(InboundMessage.classification_status == InboundMailClassificationStatus.PENDING.value)
        .order_by(InboundMessage.received_at.desc(), InboundMessage.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def classify_inbound_message(db: Session, message_id: uuid.UUID) -> InboundMessage | None:
    message = get_inbound_message_for_classification(db, message_id)
    if not message:
        return None

    if message.classification_status != InboundMailClassificationStatus.PENDING.value:
        logger.info(
            "inbound_message_classification_skipped",
            inbound_message_id=str(message.id),
            classification_status=message.classification_status,
        )
        return message

    role = LLMRole.EXECUTOR
    model = resolve_model_for_role(role)
    try:
        result = llm_classify_inbound_reply(
            business_name=message.lead.business_name if message.lead else None,
            industry=message.lead.industry if message.lead else None,
            city=message.lead.city if message.lead else None,
            lead_email=message.lead.email if message.lead else None,
            outbound_subject=message.delivery.subject_snapshot if message.delivery else None,
            outbound_message_id=message.delivery.provider_message_id if message.delivery else None,
            from_email=message.from_email,
            to_email=message.to_email,
            subject=message.subject,
            body_text=message.body_text,
            role=role,
        )
        label = _normalize_label(result.get("label"))
        if label not in VALID_REPLY_LABELS:
            raise ReplyClassificationError(f"Invalid label returned by executor: {label!r}")

        message.classification_status = InboundMailClassificationStatus.CLASSIFIED.value
        message.classification_label = label
        message.summary = _clean_text(result.get("summary"))
        message.confidence = _normalize_confidence(result.get("confidence"))
        message.next_action_suggestion = _clean_text(result.get("next_action_suggestion"))
        message.should_escalate_reviewer = _should_escalate_reviewer(
            label=label,
            confidence=message.confidence,
            llm_flag=bool(result.get("should_escalate_reviewer")),
        )
        message.classification_error = None
        message.classification_role = role.value
        message.classification_model = model
        message.classified_at = datetime.now(UTC)
        db.commit()
        db.refresh(message)
       # Emit notification for actionable classification results
        try:
            from app.services.notification_emitter import on_reply_classified
            on_reply_classified(
                db,
                message_id=message.id,
                label=message.classification_label,
                business_name=message.lead.business_name if message.lead else None,
                from_email=message.from_email,
                confidence=message.confidence,
                should_escalate=message.should_escalate_reviewer,
            )
        except Exception:
            pass  # notification failure must not break classification

        logger.info(
            "inbound_message_classified",
            inbound_message_id=str(message.id),
            lead_id=str(message.lead_id) if message.lead_id else None,
            role=role.value,
            model=model,
            label=message.classification_label,
            confidence=message.confidence,
            should_escalate_reviewer=message.should_escalate_reviewer,
        )
        return message
    except (LLMError, ReplyClassificationError, ValueError, TypeError, Exception) as exc:
        message.classification_status = InboundMailClassificationStatus.FAILED.value
        message.classification_error = str(exc)
        message.classification_role = role.value
        message.classification_model = model
        db.commit()
        db.refresh(message)

        logger.warning(
            "inbound_message_classification_failed",
            inbound_message_id=str(message.id),
            lead_id=str(message.lead_id) if message.lead_id else None,
            role=role.value,
            model=model,
            error=message.classification_error,
        )
        return message


def classify_pending_inbound_messages(
    db: Session, *, limit: int = 25
) -> list[InboundMessage]:
    messages = list_pending_inbound_messages(db, limit=limit)
    return [classify_inbound_message(db, message.id) for message in messages if message]


def _normalize_label(value: str | None) -> str:
    if not value:
        raise ReplyClassificationError("Executor did not return a label.")
    return value.strip().lower()


def _normalize_confidence(value: object) -> float | None:
    if value is None or value == "":
        return None
    confidence = float(value)
    if confidence < 0 or confidence > 1:
        raise ReplyClassificationError("Confidence must be between 0 and 1.")
    return confidence


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _should_escalate_reviewer(
    *, label: str, confidence: float | None, llm_flag: bool
) -> bool:
    if llm_flag:
        return True
    if label == "needs_human_review":
        return True
    if label in settings.mail_use_reviewer_for_labels:
        return True
    if confidence is not None and confidence < 0.45:
        return True
    return False
