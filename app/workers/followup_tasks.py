"""Celery beat task that flags CONTACTED leads without any inbound reply.

Emits one operator-facing notification per eligible lead. No outbound
message is sent automatically — the operator decides the follow-up move.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.notification import NotificationCategory, NotificationSeverity
from app.models.settings import OperationalSettings
from app.services.notifications.notification_emitter import _emit
from app.services.outreach.followup_service import find_leads_needing_followup
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.followup_tasks.task_check_followup",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=60,
)
def task_check_followup(self) -> dict:
    """Scan for leads needing follow-up; emit one notification per lead."""
    with SessionLocal() as db:
        ops = db.get(OperationalSettings, 1)
        followup_days = getattr(ops, "followup_days", 3) if ops else 3

        leads = find_leads_needing_followup(db, followup_days)
        emitted = 0

        for lead in leads:
            _emit(
                db,
                type="followup_needed",
                category=NotificationCategory.BUSINESS,
                severity=NotificationSeverity.WARNING,
                title=f"Follow-up pendiente — {lead.business_name}",
                message=(
                    f"Lead contactado hace {followup_days}+ días sin respuesta. "
                    "Considerá un follow-up manual o reclasificar."
                ),
                source_kind="lead",
                source_id=lead.id,
                metadata={
                    "business_name": lead.business_name,
                    "city": lead.city,
                    "followup_days": followup_days,
                },
                dedup_key=f"followup_needed:{lead.id}",
            )
            emitted += 1

        db.commit()

    result = {"status": "ok", "leads_flagged": emitted, "followup_days": followup_days}
    logger.info("followup_check_done", **result)
    return result
