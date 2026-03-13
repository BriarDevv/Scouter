import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.client import review_inbound_reply as llm_review_inbound_reply
from app.llm.client import review_lead as llm_review_lead
from app.llm.client import review_outreach_draft as llm_review_outreach_draft
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole
from app.models.inbound_mail import InboundMessage
from app.models.lead import Lead
from app.models.outreach import OutreachDraft

logger = get_logger(__name__)


def review_lead_with_reviewer(db: Session, lead_id: uuid.UUID) -> dict | None:
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    role = LLMRole.REVIEWER
    model = resolve_model_for_role(role)
    result = llm_review_lead(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        llm_summary=lead.llm_summary,
        llm_suggested_angle=lead.llm_suggested_angle,
        signals=list(lead.signals),
        score=lead.score,
        role=role,
    )
    payload = {
        "lead_id": lead.id,
        "business_name": lead.business_name,
        "role": role,
        "model": model,
        **result,
    }
    logger.info(
        "review_lead_completed",
        lead_id=str(lead.id),
        role=role.value,
        model=model,
        verdict=payload["verdict"],
    )
    return payload


def review_draft_with_reviewer(db: Session, draft_id: uuid.UUID) -> dict | None:
    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        return None

    lead = draft.lead
    if lead is None:
        return None

    role = LLMRole.REVIEWER
    model = resolve_model_for_role(role)
    result = llm_review_outreach_draft(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        llm_summary=lead.llm_summary,
        llm_suggested_angle=lead.llm_suggested_angle,
        signals=list(lead.signals),
        subject=draft.subject,
        body=draft.body,
        role=role,
    )
    payload = {
        "draft_id": draft.id,
        "lead_id": lead.id,
        "business_name": lead.business_name,
        "role": role,
        "model": model,
        **result,
    }
    logger.info(
        "review_draft_completed",
        draft_id=str(draft.id),
        lead_id=str(lead.id),
        role=role.value,
        model=model,
        verdict=payload["verdict"],
    )
    return payload


def review_inbound_message_with_reviewer(db: Session, message_id: uuid.UUID) -> dict | None:
    message = db.get(InboundMessage, message_id)
    if not message:
        return None

    lead = message.lead
    delivery = message.delivery
    role = LLMRole.REVIEWER
    model = resolve_model_for_role(role)
    result = llm_review_inbound_reply(
        business_name=lead.business_name if lead else None,
        industry=lead.industry if lead else None,
        city=lead.city if lead else None,
        lead_email=lead.email if lead else None,
        outbound_subject=delivery.subject_snapshot if delivery else None,
        outbound_message_id=delivery.provider_message_id if delivery else None,
        from_email=message.from_email,
        to_email=message.to_email,
        subject=message.subject,
        body_text=message.body_text,
        classification_label=message.classification_label,
        classification_summary=message.summary,
        next_action_suggestion=message.next_action_suggestion,
        should_escalate_reviewer=message.should_escalate_reviewer,
        role=role,
    )
    payload = {
        "inbound_message_id": message.id,
        "thread_id": message.thread_id,
        "lead_id": message.lead_id,
        "business_name": lead.business_name if lead else None,
        "classification_label": message.classification_label,
        "role": role,
        "model": model,
        **result,
    }
    logger.info(
        "review_inbound_reply_completed",
        inbound_message_id=str(message.id),
        lead_id=str(message.lead_id) if message.lead_id else None,
        role=role.value,
        model=model,
        verdict=payload["verdict"],
    )
    return payload
