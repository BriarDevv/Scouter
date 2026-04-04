"""API router for notifications."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.session import get_db
from app.schemas.notification import (
    NotificationBulkAction,
    NotificationCountsResponse,
    NotificationListResponse,
    NotificationResponse,
    NotificationStatusUpdate,
)
from app.services.notifications.notification_service import (
    bulk_update_notifications,
    get_notification,
    get_notification_counts,
    list_notifications,
    update_notification_status,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    type: str | None = None,
    db=Depends(get_db),
):
    items, total, unread_count = list_notifications(
        db, page=page, page_size=page_size, category=category,
        severity=severity, status=status, type=type,
    )
    return NotificationListResponse(
        items=[_to_response(n) for n in items],
        total=total, page=page, page_size=page_size, unread_count=unread_count,
    )


@router.get("/counts", response_model=NotificationCountsResponse)
def counts(db=Depends(get_db)):
    return get_notification_counts(db)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notif(notification_id: UUID, db=Depends(get_db)):
    notif = get_notification(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada.")
    return _to_response(notif)


@router.patch("/{notification_id}", response_model=NotificationResponse)
def patch_notif(notification_id: UUID, body: NotificationStatusUpdate, db=Depends(get_db)):
    if body.status not in ("read", "acknowledged", "resolved"):
        raise HTTPException(status_code=422, detail="Estado invalido.")
    notif = update_notification_status(db, notification_id, body.status)
    if not notif:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada.")
    return _to_response(notif)


@router.post("/bulk", response_model=dict)
def bulk_action(body: NotificationBulkAction, db=Depends(get_db)):
    if body.action not in ("mark_read", "mark_resolved"):
        raise HTTPException(status_code=422, detail="Accion invalida.")
    count = bulk_update_notifications(db, ids=body.ids, action=body.action, category=body.category)
    return {"affected": count}


def _to_response(n) -> NotificationResponse:
    return NotificationResponse(
        id=n.id,
        type=n.type,
        category=n.category.value if hasattr(n.category, "value") else n.category,
        severity=n.severity.value if hasattr(n.severity, "value") else n.severity,
        title=n.title,
        message=n.message,
        source_kind=n.source_kind,
        source_id=n.source_id,
        metadata=n.metadata_,
        status=n.status.value if hasattr(n.status, "value") else n.status,
        read_at=n.read_at,
        acknowledged_at=n.acknowledged_at,
        resolved_at=n.resolved_at,
        channel_state=n.channel_state,
        created_at=n.created_at,
        updated_at=n.updated_at,
    )
