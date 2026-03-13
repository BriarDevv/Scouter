import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.client import review_lead as llm_review_lead
from app.llm.client import review_outreach_draft as llm_review_outreach_draft
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole
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
