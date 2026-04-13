import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.suppression import SuppressionEntry
from app.schemas.suppression import SuppressionCreate

logger = get_logger(__name__)


def add_to_suppression_list(db: Session, data: SuppressionCreate) -> SuppressionEntry:
    """Add an email/domain/phone to the suppression list and suppress matching leads."""
    entry = SuppressionEntry(
        email=data.email.lower() if data.email else None,
        domain=data.domain.lower() if data.domain else None,
        phone=data.phone,
        reason=data.reason,
    )
    db.add(entry)

    # Suppress any matching active leads
    suppressed_count = 0
    if data.email:
        leads = (
            db.execute(
                select(Lead).where(
                    Lead.email == data.email.lower(), Lead.status != LeadStatus.SUPPRESSED
                )
            )
            .scalars()
            .all()
        )
        for lead in leads:
            lead.status = LeadStatus.SUPPRESSED
            suppressed_count += 1

    db.flush()
    db.refresh(entry)

    logger.info(
        "suppression_added",
        email=data.email,
        domain=data.domain,
        suppressed_leads=suppressed_count,
    )
    return entry


def list_suppression(db: Session, page: int = 1, page_size: int = 50) -> list[SuppressionEntry]:
    stmt = (
        select(SuppressionEntry)
        .order_by(SuppressionEntry.added_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.execute(stmt).scalars().all())


def remove_from_suppression(db: Session, entry_id: uuid.UUID) -> bool:
    entry = db.get(SuppressionEntry, entry_id)
    if not entry:
        return False
    db.delete(entry)
    db.flush()
    logger.info("suppression_removed", entry_id=str(entry_id))
    return True
