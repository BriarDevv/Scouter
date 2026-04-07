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
from app.models.review_correction import CorrectionCategory, CorrectionSeverity, ReviewCorrection
from app.services.settings.operational_settings_service import get_cached_settings

logger = get_logger(__name__)


def _persist_corrections(
    db: Session,
    *,
    lead_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
    review_type: str,
    corrections: list[dict],
    model: str | None,
) -> int:
    """Extract structured corrections from reviewer output and persist them.

    Returns the number of corrections stored.
    """
    count = 0
    for c in corrections:
        raw_category = c.get("category", "relevance")
        raw_severity = c.get("severity", "suggestion")
        try:
            category = CorrectionCategory(raw_category)
        except ValueError:
            category = CorrectionCategory.RELEVANCE
        try:
            severity = CorrectionSeverity(raw_severity)
        except ValueError:
            severity = CorrectionSeverity.SUGGESTION

        rc = ReviewCorrection(
            lead_id=lead_id,
            pipeline_run_id=pipeline_run_id,
            review_type=review_type,
            category=category,
            severity=severity,
            issue=c.get("issue", ""),
            suggestion=c.get("suggestion"),
            model=model,
        )
        db.add(rc)
        count += 1

    if count:
        db.flush()
        logger.info(
            "review_corrections_persisted",
            review_type=review_type,
            lead_id=str(lead_id),
            count=count,
        )
    return count


def review_lead_with_reviewer(db: Session, lead_id: uuid.UUID) -> dict | None:
    ops = get_cached_settings(db)
    if not ops.reviewer_enabled:
        logger.info("reviewer_disabled_by_settings", action="review_lead", lead_id=str(lead_id))
        return None

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

    # Persist structured corrections if present
    corrections = result.get("corrections", [])
    if corrections:
        _persist_corrections(
            db,
            lead_id=lead.id,
            pipeline_run_id=None,
            review_type="lead_review",
            corrections=corrections,
            model=model,
        )

    logger.info(
        "review_lead_completed",
        lead_id=str(lead.id),
        role=role.value,
        model=model,
        verdict=payload["verdict"],
        corrections_count=len(corrections),
    )
    return payload


def review_draft_with_reviewer(db: Session, draft_id: uuid.UUID) -> dict | None:
    ops = get_cached_settings(db)
    if not ops.reviewer_enabled:
        logger.info("reviewer_disabled_by_settings", action="review_draft", draft_id=str(draft_id))
        return None

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

    # Persist structured corrections if present
    corrections = result.get("corrections", [])
    if corrections:
        _persist_corrections(
            db,
            lead_id=lead.id,
            pipeline_run_id=None,
            review_type="draft_review",
            corrections=corrections,
            model=model,
        )

    # Auto-apply revised content when Reviewer suggests revisions
    revised_body = result.get("revised_body")
    revised_subject = result.get("revised_subject")
    if payload["verdict"] == "revise" and revised_body:
        draft.body = revised_body
        if revised_subject:
            draft.subject = revised_subject
        db.flush()
        logger.info(
            "review_draft_auto_applied",
            draft_id=str(draft.id),
            lead_id=str(lead.id),
            has_revised_subject=bool(revised_subject),
        )

    logger.info(
        "review_draft_completed",
        draft_id=str(draft.id),
        lead_id=str(lead.id),
        role=role.value,
        model=model,
        verdict=payload["verdict"],
        corrections_count=len(corrections),
    )
    return payload


def review_inbound_message_with_reviewer(db: Session, message_id: uuid.UUID) -> dict | None:
    ops = get_cached_settings(db)
    if not ops.reviewer_enabled:
        logger.info(
            "reviewer_disabled_by_settings", action="review_inbound", message_id=str(message_id)
        )
        return None

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
