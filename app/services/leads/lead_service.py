import hashlib
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.outreach import LogAction, OutreachLog
from app.models.suppression import SuppressionEntry
from app.schemas.lead import LeadCreate, LeadUpdate

logger = get_logger(__name__)


def _compute_dedup_hash(business_name: str, city: str | None, website_url: str | None) -> str:
    """Generate a dedup fingerprint from normalized fields."""
    parts = [
        business_name.strip().lower(),
        (city or "").strip().lower(),
        (website_url or "").strip().lower().rstrip("/"),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def is_suppressed(db: Session, email: str | None, domain: str | None = None) -> bool:
    """Check if an email or domain is in the suppression list."""
    if not email and not domain:
        return False
    conditions = []
    if email:
        conditions.append(SuppressionEntry.email == email.lower())
    if domain:
        conditions.append(SuppressionEntry.domain == domain.lower())
    stmt = select(SuppressionEntry.id).where(or_(*conditions)).limit(1)
    return db.execute(stmt).first() is not None


def create_lead(db: Session, data: LeadCreate) -> Lead:
    """Create a new lead with dedup check and suppression check."""
    # Check suppression
    if data.email and is_suppressed(db, email=data.email):
        raise ValueError(f"Email {data.email} is in the suppression list")

    # Compute dedup hash
    dedup_hash = _compute_dedup_hash(data.business_name, data.city, data.website_url)

    # Check for duplicate
    existing = db.execute(select(Lead).where(Lead.dedup_hash == dedup_hash)).scalar_one_or_none()
    if existing:
        logger.info("duplicate_lead_skipped", lead_id=str(existing.id), hash=dedup_hash)
        return existing

    lead = Lead(
        **data.model_dump(exclude_unset=True),
        dedup_hash=dedup_hash,
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.flush()
    db.refresh(lead)
    logger.info("lead_created", lead_id=str(lead.id), business=lead.business_name)
    return lead


def get_lead(db: Session, lead_id: uuid.UUID) -> Lead | None:
    return db.get(Lead, lead_id)


def list_leads(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    status: LeadStatus | None = None,
    min_score: float | None = None,
) -> tuple[list[Lead], int]:
    """List leads with pagination and optional filters."""
    stmt = select(Lead)
    count_stmt = select(func.count(Lead.id))

    if status:
        stmt = stmt.where(Lead.status == status)
        count_stmt = count_stmt.where(Lead.status == status)
    if min_score is not None:
        stmt = stmt.where(Lead.score >= min_score)
        count_stmt = count_stmt.where(Lead.score >= min_score)

    total = db.execute(count_stmt).scalar() or 0
    leads = (
        db.execute(
            stmt.order_by(Lead.score.desc().nulls_last(), Lead.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(leads), total


def query_leads_for_export(
    db: Session,
    status: str | None = None,
    quality: str | None = None,
) -> list[Lead]:
    """Return leads matching export filters, ordered by newest first."""
    query = select(Lead)
    if status:
        query = query.where(Lead.status == status)
    if quality:
        query = query.where(Lead.llm_quality == quality)
    query = query.order_by(Lead.created_at.desc())
    return list(db.execute(query).scalars().yield_per(100))


def list_lead_names(db: Session, limit: int = 5000) -> list[Lead]:
    """Return lightweight (id, business_name) rows for all leads."""
    return list(
        db.execute(
            select(Lead.id, Lead.business_name).order_by(Lead.business_name).limit(limit)
        ).all()
    )


def update_lead(db: Session, lead_id: uuid.UUID, data: LeadUpdate) -> Lead | None:
    lead = db.get(Lead, lead_id)
    if not lead:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.flush()
    db.refresh(lead)
    return lead


def update_lead_status(db: Session, lead_id: uuid.UUID, status: LeadStatus) -> Lead | None:
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    previous_status = lead.status
    lead.status = status

    # Emit immutable event for timeline / analytics (US-005 post-hardening).
    # Only on real transitions — repeated set to same status is noise.
    if previous_status != status:
        try:
            from app.services.leads.event_service import emit_lead_event

            emit_lead_event(
                db,
                lead_id=lead.id,
                event_type="status_changed",
                old_status=previous_status.value if previous_status else None,
                new_status=status.value,
                actor="user",
            )
        except Exception as exc:
            logger.warning("lead_event_emit_failed", lead_id=str(lead.id), error=str(exc))

    log_action = {
        LeadStatus.APPROVED: LogAction.APPROVED,
        LeadStatus.CONTACTED: LogAction.SENT,
        LeadStatus.OPENED: LogAction.OPENED,
        LeadStatus.REPLIED: LogAction.REPLIED,
        LeadStatus.MEETING: LogAction.MEETING,
        LeadStatus.WON: LogAction.WON,
        LeadStatus.LOST: LogAction.LOST,
    }.get(status)

    if log_action and previous_status != status:
        db.add(
            OutreachLog(
                lead_id=lead.id,
                draft_id=None,
                action=log_action,
                actor="user",
                detail=f"Lead status updated from {previous_status.value} to {status.value}",
            )
        )

    db.flush()
    db.refresh(lead)
    logger.info(
        "lead_status_updated",
        lead_id=str(lead.id),
        previous_status=previous_status.value,
        status=status.value,
    )

    # Capture outcome snapshot when lead reaches terminal state (WON/LOST)
    if status in (LeadStatus.WON, LeadStatus.LOST):
        try:
            from app.services.pipeline.outcome_tracking_service import capture_outcome_snapshot

            capture_outcome_snapshot(db, lead.id, status.value)
        except Exception as exc:
            logger.warning("outcome_snapshot_failed", lead_id=str(lead.id), error=str(exc))

    return lead
