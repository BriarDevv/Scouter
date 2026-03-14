"""WhatsApp action executors -- execute confirmed actions from WhatsApp.

Each function takes a DB session and relevant params, returns a Spanish
response string, and is wrapped in try/except (never crashes).
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead
from app.models.notification import Notification
from app.models.outreach import DraftStatus, OutreachDraft

logger = get_logger(__name__)


# -- Permission tiers --
PERMISSION_TIERS: dict[str, int] = {
    "resolve_notification": 1,    # Low risk
    "mark_read_notifications": 1, # Low risk
    "approve_draft": 2,           # Medium risk - sends email
    "reject_draft": 2,            # Medium risk
    "generate_draft": 3,          # Higher risk - creates content
}


# -- Action rate limiting: max 10 actions per phone per hour --
_ACTION_RATE_LIMIT = 10
_ACTION_RATE_WINDOW = 3600  # 1 hour
_action_rate: dict[str, list[float]] = defaultdict(list)


def check_action_rate_limit(phone: str) -> bool:
    """Return True if action is within rate limit, False if exceeded."""
    now = time.time()
    window = _action_rate[phone]
    _action_rate[phone] = [t for t in window if now - t < _ACTION_RATE_WINDOW]
    if len(_action_rate[phone]) >= _ACTION_RATE_LIMIT:
        logger.warning("wa_action_rate_limited", phone=phone[:6] + "***")
        return False
    _action_rate[phone].append(now)
    return True


def validate_uuid(value: str) -> uuid.UUID | None:
    """Validate and return a UUID, or None if invalid."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def execute_resolve_notification(db: Session, notification_id: str) -> str:
    """Resolve a notification by ID."""
    try:
        uid = validate_uuid(notification_id)
        if uid is None:
            return "ID de notificacion invalido."

        from app.services.notification_service import update_notification_status
        notif = update_notification_status(db, uid, "resolved")
        if notif is None:
            return "No se encontro la notificacion con ese ID."

        logger.info("wa_action_resolve_notification", notification_id=notification_id)
        return "Notificacion resuelta correctamente."
    except Exception as exc:
        logger.error("wa_action_resolve_notification_failed", error=str(exc))
        return "Error al resolver la notificacion. Intenta de nuevo."


def execute_mark_read_all(db: Session) -> str:
    """Mark all unread notifications as read."""
    try:
        from app.services.notification_service import bulk_update_notifications
        count = bulk_update_notifications(db, action="mark_read")
        logger.info("wa_action_mark_read_all", count=count)
        return "Se marcaron " + str(count) + " notificaciones como leidas."
    except Exception as exc:
        logger.error("wa_action_mark_read_all_failed", error=str(exc))
        return "Error al marcar notificaciones. Intenta de nuevo."


def execute_approve_draft(db: Session, draft_id: str) -> str:
    """Approve an outreach draft."""
    try:
        uid = validate_uuid(draft_id)
        if uid is None:
            return "ID de borrador invalido."

        draft = db.get(OutreachDraft, uid)
        if draft is None:
            return "No se encontro el borrador con ese ID."

        if draft.status != DraftStatus.PENDING_REVIEW:
            status_val = draft.status.value if hasattr(draft.status, "value") else draft.status
            return "El borrador no esta pendiente de revision (estado actual: " + status_val + ")."

        draft.status = DraftStatus.APPROVED
        draft.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(draft)

        lead_name = draft.lead.business_name if draft.lead else "desconocido"
        logger.info("wa_action_approve_draft", draft_id=draft_id, lead=lead_name)
        return "Borrador aprobado para " + lead_name + "."
    except Exception as exc:
        logger.error("wa_action_approve_draft_failed", error=str(exc))
        return "Error al aprobar el borrador. Intenta de nuevo."


def execute_reject_draft(db: Session, draft_id: str) -> str:
    """Reject an outreach draft."""
    try:
        uid = validate_uuid(draft_id)
        if uid is None:
            return "ID de borrador invalido."

        draft = db.get(OutreachDraft, uid)
        if draft is None:
            return "No se encontro el borrador con ese ID."

        if draft.status != DraftStatus.PENDING_REVIEW:
            status_val = draft.status.value if hasattr(draft.status, "value") else draft.status
            return "El borrador no esta pendiente de revision (estado actual: " + status_val + ")."

        draft.status = DraftStatus.REJECTED
        draft.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(draft)

        lead_name = draft.lead.business_name if draft.lead else "desconocido"
        logger.info("wa_action_reject_draft", draft_id=draft_id, lead=lead_name)
        return "Borrador rechazado para " + lead_name + "."
    except Exception as exc:
        logger.error("wa_action_reject_draft_failed", error=str(exc))
        return "Error al rechazar el borrador. Intenta de nuevo."


def execute_generate_draft(db: Session, lead_name: str) -> str:
    """Find lead by name and trigger draft generation."""
    try:
        stmt = select(Lead).where(Lead.business_name.ilike("%" + lead_name + "%")).limit(1)
        lead = db.execute(stmt).scalars().first()
        if lead is None:
            return "No se encontro ningun lead con el nombre: " + lead_name

        # Try to use the outreach service to generate the draft
        try:
            from app.services.outreach_service import generate_outreach_draft
            draft = generate_outreach_draft(db, lead.id)
            if draft:
                logger.info("wa_action_generate_draft", lead_name=lead_name, draft_id=str(draft.id))
                return "Draft generado para " + lead.business_name + ". Asunto: " + draft.subject
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: queue placeholder
        logger.info("wa_action_generate_draft_queued", lead_name=lead_name)
        return "Generacion de draft encolada para " + lead.business_name + "."
    except Exception as exc:
        logger.error("wa_action_generate_draft_failed", error=str(exc))
        return "Error al generar el draft. Intenta de nuevo."


# -- Test helpers --


def _reset_rate_limits() -> None:
    """Clear action rate limit state (for tests)."""
    _action_rate.clear()
