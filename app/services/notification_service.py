"""Notification service — create, query, update, and dispatch notifications.

Supports deduplication, rate limiting, and multi-channel delivery (in-app + WhatsApp).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
)

logger = get_logger(__name__)

_RATE_LIMIT_WINDOW = timedelta(minutes=15)
_RATE_LIMIT_MAX = 3

_SEV_ORDER = {"info": 0, "warning": 1, "high": 2, "critical": 3}


def create_notification(
    db: Session,
    *,
    type: str,
    category: NotificationCategory | str,
    severity: NotificationSeverity | str,
    title: str,
    message: str,
    source_kind: str | None = None,
    source_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    dedup_key: str | None = None,
) -> Notification | None:
    """Create a notification with dedup and rate-limit guards.

    Returns None if deduplicated or rate-limited.
    """
    if isinstance(category, str):
        category = NotificationCategory(category)
    if isinstance(severity, str):
        severity = NotificationSeverity(severity)

    # Dedup guard
    if dedup_key:
        exists = db.execute(
            select(Notification.id).where(Notification.dedup_key == dedup_key)
        ).scalar_one_or_none()
        if exists:
            logger.debug("notification_deduplicated", dedup_key=dedup_key)
            return None

    # Rate-limit guard: same type + source within window
    if source_kind and source_id:
        cutoff = datetime.now(timezone.utc) - _RATE_LIMIT_WINDOW
        recent = db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.type == type,
                Notification.source_kind == source_kind,
                Notification.source_id == source_id,
                Notification.created_at >= cutoff,
            )
        ).scalar_one()
        if recent >= _RATE_LIMIT_MAX:
            logger.debug("notification_rate_limited", type=type, source_kind=source_kind)
            return None

    notif = Notification(
        type=type,
        category=category,
        severity=severity,
        title=title,
        message=message,
        source_kind=source_kind,
        source_id=source_id,
        metadata_=metadata,
        status=NotificationStatus.UNREAD,
        channel_state={"in_app": "delivered"},
    )
    if dedup_key:
        notif.dedup_key = dedup_key

    try:
        db.add(notif)
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.debug("notification_dedup_integrity", dedup_key=dedup_key)
        return None

    # Dispatch WhatsApp if thresholds met
    _maybe_dispatch_whatsapp(db, notif)

    db.commit()
    db.refresh(notif)
    logger.info(
        "notification_created",
        notification_id=str(notif.id),
        type=type,
        category=category.value,
        severity=severity.value,
    )
    return notif


def list_notifications(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    type: str | None = None,
) -> tuple[list[Notification], int, int]:
    """Return (items, total, unread_count)."""
    q = select(Notification)
    count_q = select(func.count()).select_from(Notification)

    filters = []
    if category:
        filters.append(Notification.category == category)
    if severity:
        filters.append(Notification.severity == severity)
    if status:
        filters.append(Notification.status == status)
    if type:
        filters.append(Notification.type == type)

    for f in filters:
        q = q.where(f)
        count_q = count_q.where(f)

    total = db.execute(count_q).scalar_one()
    unread_count = db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.status == NotificationStatus.UNREAD
        )
    ).scalar_one()

    items = list(
        db.execute(
            q.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).scalars().all()
    )
    return items, total, unread_count


def get_notification(db: Session, notification_id: uuid.UUID) -> Notification | None:
    return db.get(Notification, notification_id)


def get_notification_counts(db: Session) -> dict:
    """Summary counts for the notification badge."""
    rows = db.execute(
        select(Notification.category, Notification.severity, func.count())
        .where(Notification.status == NotificationStatus.UNREAD)
        .group_by(Notification.category, Notification.severity)
    ).all()

    result = {"total_unread": 0, "business": 0, "system": 0, "security": 0, "critical": 0, "high": 0}
    for cat, sev, cnt in rows:
        result["total_unread"] += cnt
        if cat in result:
            result[cat] += cnt
        if sev in ("critical", "high"):
            result[sev] += cnt
    return result


def update_notification_status(
    db: Session, notification_id: uuid.UUID, new_status: str
) -> Notification | None:
    notif = db.get(Notification, notification_id)
    if not notif:
        return None

    now = datetime.now(timezone.utc)
    notif.status = NotificationStatus(new_status)
    if new_status == "read":
        notif.read_at = notif.read_at or now
    elif new_status == "acknowledged":
        notif.read_at = notif.read_at or now
        notif.acknowledged_at = notif.acknowledged_at or now
    elif new_status == "resolved":
        notif.read_at = notif.read_at or now
        notif.resolved_at = notif.resolved_at or now

    db.commit()
    db.refresh(notif)
    return notif


def bulk_update_notifications(
    db: Session,
    *,
    ids: list[uuid.UUID] | None = None,
    action: str,
    category: str | None = None,
) -> int:
    """Bulk mark notifications. Returns count affected."""
    now = datetime.now(timezone.utc)
    stmt = update(Notification)

    if ids:
        stmt = stmt.where(Notification.id.in_(ids))
    elif category:
        stmt = stmt.where(
            Notification.category == category,
            Notification.status == NotificationStatus.UNREAD,
        )
    else:
        stmt = stmt.where(Notification.status == NotificationStatus.UNREAD)

    if action == "mark_read":
        stmt = stmt.values(status=NotificationStatus.READ, read_at=now)
    elif action == "mark_resolved":
        stmt = stmt.values(status=NotificationStatus.RESOLVED, read_at=now, resolved_at=now)
    else:
        return 0

    result = db.execute(stmt)
    db.commit()
    return result.rowcount


def _maybe_dispatch_whatsapp(db: Session, notif: Notification) -> None:
    """Send WhatsApp alert if notification meets severity/category thresholds."""
    from app.services.operational_settings_service import get_or_create as get_settings

    settings = get_or_create(db)
    if not getattr(settings, "whatsapp_alerts_enabled", False):
        return

    min_sev = getattr(settings, "whatsapp_min_severity", "high")
    if _SEV_ORDER.get(notif.severity.value, 0) < _SEV_ORDER.get(min_sev, 2):
        return

    allowed_cats = getattr(settings, "whatsapp_categories", None) or ["business", "security"]
    if notif.category.value not in allowed_cats:
        return

    # Anti-loop: never send WhatsApp alert about WhatsApp failure
    if notif.type == "whatsapp_delivery_failed":
        return

    try:
        from app.services.whatsapp_service import send_alert
        result = send_alert(db, title=notif.title, message=notif.message, severity=notif.severity.value)
        notif.channel_state = {
            **(notif.channel_state or {}),
            "whatsapp": "sent" if result else "failed",
        }
    except Exception as exc:
        logger.error("whatsapp_dispatch_failed", error=str(exc))
        notif.channel_state = {
            **(notif.channel_state or {}),
            "whatsapp": "failed",
            "whatsapp_error": str(exc)[:200],
        }


def get_or_create(db: Session) -> None:
    """Alias used internally — not needed for notifications."""
    pass
