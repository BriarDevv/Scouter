import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, LogAction, OutreachDraft, OutreachLog
from app.outreach.generator import generate_draft_content
from app.services.lead_service import is_suppressed

logger = get_logger(__name__)


def get_draft(db: Session, draft_id: uuid.UUID) -> OutreachDraft | None:
    return db.get(OutreachDraft, draft_id)


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
    db.flush()

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
    stmt = stmt.order_by(OutreachDraft.generated_at.desc()).offset((page - 1) * page_size).limit(page_size)
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

    db.commit()
    db.refresh(draft)
    logger.info(
        "outreach_draft_updated",
        draft_id=str(draft.id),
        previous_status=previous_status.value,
        status=draft.status.value,
    )
    return draft
