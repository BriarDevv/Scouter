import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, LogAction, OutreachDraft, OutreachLog
from app.outreach.generator import generate_draft_content
from app.services.lead_service import is_suppressed

logger = get_logger(__name__)


def generate_outreach_draft(db: Session, lead_id: uuid.UUID) -> OutreachDraft | None:
    """Generate an outreach email draft for a lead using LLM."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    # Check suppression before generating
    if lead.email and is_suppressed(db, email=lead.email):
        logger.warning("outreach_blocked_suppressed", lead_id=str(lead_id))
        return None

    subject, body = generate_draft_content(lead)

    draft = OutreachDraft(
        lead_id=lead.id,
        subject=subject,
        body=body,
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)

    # Log generation
    db.add(OutreachLog(
        lead_id=lead.id,
        draft_id=draft.id,
        action=LogAction.GENERATED,
        actor="system",
    ))

    lead.status = LeadStatus.DRAFT_READY
    db.commit()
    db.refresh(draft)

    logger.info("outreach_draft_generated", lead_id=str(lead_id), draft_id=str(draft.id))
    return draft


def review_draft(
    db: Session, draft_id: uuid.UUID, approved: bool, feedback: str | None = None
) -> OutreachDraft | None:
    """Human review: approve or reject a draft."""
    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        return None

    from datetime import datetime, timezone

    draft.status = DraftStatus.APPROVED if approved else DraftStatus.REJECTED
    draft.reviewed_at = datetime.now(timezone.utc)

    action = LogAction.APPROVED if approved else LogAction.REJECTED
    db.add(OutreachLog(
        lead_id=draft.lead_id,
        draft_id=draft.id,
        action=action,
        actor="user",
        detail=feedback,
    ))

    if approved:
        lead = db.get(Lead, draft.lead_id)
        if lead:
            lead.status = LeadStatus.APPROVED

    db.commit()
    db.refresh(draft)

    logger.info("outreach_draft_reviewed", draft_id=str(draft_id), approved=approved)
    return draft


def list_drafts(
    db: Session,
    status: DraftStatus | None = None,
    page: int = 1,
    page_size: int = 50,
) -> list[OutreachDraft]:
    stmt = select(OutreachDraft)
    if status:
        stmt = stmt.where(OutreachDraft.status == status)
    stmt = stmt.order_by(OutreachDraft.generated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    return list(db.execute(stmt).scalars().all())
