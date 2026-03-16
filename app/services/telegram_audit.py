"""Telegram audit service — append-only compliance log for all conversations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.telegram_audit import TelegramAuditLog, TelegramDirection

logger = get_logger(__name__)


def log_inbound(db: Session, chat_id: str, message: str, intent: str | None) -> None:
    """Record an inbound Telegram message."""
    entry = TelegramAuditLog(
        direction=TelegramDirection.INBOUND,
        chat_id=chat_id,
        content=message,
        intent=intent,
    )
    db.add(entry)
    db.commit()
    logger.info("tg_audit_inbound", chat_id=chat_id[:6] + "***", intent=intent)


def log_outbound(db: Session, chat_id: str, response: str, latency_ms: int | None) -> None:
    """Record an outbound Telegram response."""
    entry = TelegramAuditLog(
        direction=TelegramDirection.OUTBOUND,
        chat_id=chat_id,
        content=response,
        latency_ms=latency_ms,
    )
    db.add(entry)
    db.commit()
    logger.info("tg_audit_outbound", chat_id=chat_id[:6] + "***", latency_ms=latency_ms)
