import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.invocation_metadata import clear_last_invocation, pop_last_invocation
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, LogAction, OutreachDraft, OutreachLog
from app.models.outreach_delivery import OutreachDelivery
from app.services.leads.lead_service import is_suppressed
from app.services.outreach.generator import generate_draft_content

logger = get_logger(__name__)


def _serialize_generation_metadata() -> dict | None:
    metadata = pop_last_invocation()
    return metadata.to_dict() if metadata else None


def get_draft(db: Session, draft_id: uuid.UUID) -> OutreachDraft | None:
    return db.get(OutreachDraft, draft_id)


def generate_outreach_draft(
    db: Session,
    lead_id: uuid.UUID,
    *,
    commit: bool = True,
    pipeline_context_text: str = "",
) -> OutreachDraft | None:
    """Generate an outreach email draft for a lead using LLM."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    if not lead.email:
        logger.warning("draft_skipped_no_email", lead_id=str(lead_id), business=lead.business_name)
        return None

    # Check suppression before generating
    if is_suppressed(db, email=lead.email):
        logger.warning("outreach_blocked_suppressed", lead_id=str(lead_id))
        return None

    clear_last_invocation()
    subject, body = generate_draft_content(lead, db=db, pipeline_context_text=pipeline_context_text)
    generation_metadata = _serialize_generation_metadata()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject=subject,
        body=body,
        status=DraftStatus.PENDING_REVIEW,
        generation_metadata_json=generation_metadata,
    )
    db.add(draft)
    db.flush()

    # Log generation
    db.add(
        OutreachLog(
            lead_id=lead.id,
            draft_id=draft.id,
            action=LogAction.GENERATED,
            actor="system",
            detail=(
                "ai_degraded=true; ai_fallback_used=true"
                if generation_metadata and generation_metadata.get("degraded")
                else None
            ),
        )
    )

    lead.status = LeadStatus.DRAFT_READY

    if commit:
        db.commit()
        db.refresh(draft)

    logger.info(
        "outreach_draft_generated",
        lead_id=str(lead_id),
        draft_id=str(draft.id),
        ai_fallback_used=(bool(generation_metadata and generation_metadata.get("fallback_used"))),
        ai_degraded=bool(generation_metadata and generation_metadata.get("degraded")),
    )
    return draft


def review_draft(
    db: Session, draft_id: uuid.UUID, approved: bool, feedback: str | None = None
) -> OutreachDraft | None:
    """Human review: approve or reject a draft."""
    status = DraftStatus.APPROVED if approved else DraftStatus.REJECTED
    draft = update_draft(db, draft_id, status=status, feedback=feedback)
    if draft:
        logger.info("outreach_draft_reviewed", draft_id=str(draft_id), approved=approved)
    return draft


def list_drafts(
    db: Session,
    status: DraftStatus | None = None,
    lead_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[OutreachDraft]:
    stmt = select(OutreachDraft)
    if status:
        stmt = stmt.where(OutreachDraft.status == status)
    if lead_id:
        stmt = stmt.where(OutreachDraft.lead_id == lead_id)
    stmt = (
        stmt.order_by(OutreachDraft.generated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.execute(stmt).scalars().all())


def list_logs(
    db: Session,
    lead_id: uuid.UUID | None = None,
    draft_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[OutreachLog]:
    stmt = select(OutreachLog)
    if lead_id:
        stmt = stmt.where(OutreachLog.lead_id == lead_id)
    if draft_id:
        stmt = stmt.where(OutreachLog.draft_id == draft_id)
    stmt = stmt.order_by(OutreachLog.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def update_draft(
    db: Session,
    draft_id: uuid.UUID,
    *,
    subject: str | None = None,
    body: str | None = None,
    status: DraftStatus | None = None,
    feedback: str | None = None,
    actor: str = "user",
) -> OutreachDraft | None:
    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        return None

    if subject is not None:
        draft.subject = subject
    if body is not None:
        draft.body = body

    previous_status = draft.status
    lead = db.get(Lead, draft.lead_id)

    if status and status != previous_status:
        draft.status = status

        if status in {DraftStatus.APPROVED, DraftStatus.REJECTED}:
            draft.reviewed_at = datetime.now(timezone.utc)
        if status == DraftStatus.SENT:
            draft.sent_at = datetime.now(timezone.utc)

        action = {
            DraftStatus.APPROVED: LogAction.APPROVED,
            DraftStatus.REJECTED: LogAction.REJECTED,
            DraftStatus.SENT: LogAction.SENT,
        }.get(status)
        if action:
            db.add(
                OutreachLog(
                    lead_id=draft.lead_id,
                    draft_id=draft.id,
                    action=action,
                    actor=actor,
                    detail=feedback,
                )
            )

        if lead:
            if status == DraftStatus.APPROVED:
                lead.status = LeadStatus.APPROVED
            elif status == DraftStatus.SENT:
                lead.status = LeadStatus.CONTACTED

    db.flush()
    db.refresh(draft)
    logger.info(
        "outreach_draft_updated",
        draft_id=str(draft.id),
        previous_status=previous_status.value,
        status=draft.status.value,
    )
    return draft


def generate_whatsapp_draft(
    db: Session,
    lead_id: uuid.UUID,
    *,
    commit: bool = True,
) -> OutreachDraft | None:
    """Generate a WhatsApp outreach draft for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    if not lead.phone:
        logger.warning(
            "wa_draft_skipped_no_phone",
            lead_id=str(lead_id),
            business=lead.business_name,
        )
        return None

    from app.services.outreach.generator import generate_whatsapp_draft_content

    clear_last_invocation()
    body = generate_whatsapp_draft_content(lead, db=db)
    generation_metadata = _serialize_generation_metadata()

    draft = OutreachDraft(
        lead_id=lead.id,
        channel="whatsapp",
        subject=None,
        body=body,
        status=DraftStatus.PENDING_REVIEW,
        generation_metadata_json=generation_metadata,
    )
    db.add(draft)
    db.flush()

    db.add(
        OutreachLog(
            lead_id=lead.id,
            draft_id=draft.id,
            action=LogAction.GENERATED,
            actor="system",
            detail=(
                "ai_degraded=true; ai_fallback_used=true"
                if generation_metadata and generation_metadata.get("degraded")
                else None
            ),
        )
    )

    if commit:
        db.commit()
        db.refresh(draft)

    logger.info(
        "wa_draft_generated",
        lead_id=str(lead_id),
        draft_id=str(draft.id),
        ai_fallback_used=(bool(generation_metadata and generation_metadata.get("fallback_used"))),
        ai_degraded=bool(generation_metadata and generation_metadata.get("degraded")),
    )
    return draft


def send_whatsapp_draft(db: Session, draft_id: uuid.UUID) -> "OutreachDelivery":
    """Send an approved WhatsApp draft via Kapso."""
    from datetime import datetime, timezone

    from app.models.outreach_delivery import OutreachDelivery
    from app.services.comms.kapso_service import send_whatsapp_message

    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        raise ValueError("Draft not found")
    if draft.channel != "whatsapp":
        raise ValueError("Draft is not a WhatsApp draft")
    if draft.status != DraftStatus.APPROVED:
        raise ValueError(f"Draft status is {draft.status.value}, expected approved")

    lead = db.get(Lead, draft.lead_id)
    if not lead or not lead.phone:
        raise ValueError("Lead has no phone number")

    result = send_whatsapp_message(lead.phone, draft.body)

    delivery = OutreachDelivery(
        draft_id=draft.id,
        lead_id=lead.id,
        recipient_email=lead.phone,  # reuse email field for phone
        subject_snapshot=draft.body[:500],  # WA has no subject, store body preview
        provider="kapso",
        provider_message_id=result.get("message_id"),
    )
    db.add(delivery)

    draft.status = DraftStatus.SENT
    draft.sent_at = datetime.now(timezone.utc)

    db.add(
        OutreachLog(
            lead_id=lead.id,
            draft_id=draft.id,
            action=LogAction.SENT,
            actor="system",
        )
    )

    if lead.status not in (
        LeadStatus.CONTACTED,
        LeadStatus.OPENED,
        LeadStatus.REPLIED,
        LeadStatus.MEETING,
        LeadStatus.WON,
        LeadStatus.LOST,
    ):
        lead.status = LeadStatus.CONTACTED

    db.flush()
    db.refresh(delivery)
    logger.info("wa_draft_sent", draft_id=str(draft_id), phone=lead.phone[:6] + "***")
    return delivery
