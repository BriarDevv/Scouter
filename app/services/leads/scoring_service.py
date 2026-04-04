import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.scoring.rules import compute_score

logger = get_logger(__name__)


def score_lead(db: Session, lead_id: uuid.UUID) -> Lead | None:
    """Score a lead based on its signals and data."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    score = compute_score(lead)
    lead.score = score
    lead.status = LeadStatus.SCORED
    lead.scored_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)

    logger.info("lead_scored", lead_id=str(lead_id), score=score)

    # Emit notification if score exceeds threshold
    try:
        from app.models.settings import OperationalSettings
        settings = db.query(OperationalSettings).first()
        threshold = settings.notification_score_threshold if settings else 70
        from app.services.notifications.notification_emitter import on_high_score_lead
        on_high_score_lead(
            db, lead_id=lead_id,
            business_name=lead.business_name or "Unknown",
            score=score, threshold=threshold,
        )
    except Exception:
        logger.debug("scoring_notification_failed", exc_info=True)

    return lead
