"""Emit immutable lead events for audit + analytics.

Callers should invoke emit_lead_event for any observable lead transition
(status change, pipeline step success, outreach send, operator override).
The service never commits — the caller owns the transaction so the event
lives or dies with the business change that triggered it.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead_event import LeadEvent

logger = get_logger(__name__)


def emit_lead_event(
    db: Session,
    *,
    lead_id: uuid.UUID,
    event_type: str,
    old_status: str | None = None,
    new_status: str | None = None,
    payload: dict | None = None,
    actor: str = "system",
) -> LeadEvent:
    """Insert a LeadEvent row. Caller commits."""
    event = LeadEvent(
        lead_id=lead_id,
        event_type=event_type,
        old_status=old_status,
        new_status=new_status,
        payload_json=payload,
        actor=actor,
    )
    db.add(event)
    db.flush()
    logger.debug(
        "lead_event_emitted",
        lead_id=str(lead_id),
        event_type=event_type,
        old_status=old_status,
        new_status=new_status,
        actor=actor,
    )
    return event
