"""WhatsApp audit service — append-only compliance log for all conversations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.whatsapp_audit import MessageDirection, WhatsAppAuditLog

logger = get_logger(__name__)


def log_inbound(db: Session, phone: str, message: str, intent: str | None) -> None:
    """Record an inbound WhatsApp message."""
    entry = WhatsAppAuditLog(
        direction=MessageDirection.INBOUND,
        phone=phone,
        content=message,
        intent=intent,
    )
    db.add(entry)
    db.commit()
    logger.info("wa_audit_inbound", phone=phone[:6] + "***", intent=intent)


def log_outbound(db: Session, phone: str, response: str, latency_ms: int | None) -> None:
    """Record an outbound WhatsApp response."""
    entry = WhatsAppAuditLog(
        direction=MessageDirection.OUTBOUND,
        phone=phone,
        content=response,
        latency_ms=latency_ms,
    )
    db.add(entry)
    db.commit()
    logger.info("wa_audit_outbound", phone=phone[:6] + "***", latency_ms=latency_ms)
