"""Notification tools — list, count, and mark read."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.notifications.notification_service import (
    get_notification_counts as _get_counts,
)
from app.services.notifications.notification_service import (
    list_notifications as _list,
)
from app.services.notifications.notification_service import (
    update_notification_status,
)


def list_notifications(
    db: Session,
    *,
    status: str | None = None,
    category: str | None = None,
    limit: int = 10,
) -> dict:
    """List recent notifications."""
    items, total, unread = _list(
        db,
        page=1,
        page_size=min(limit, 50),
        status=status,
        category=category,
    )
    return {
        "total": total,
        "unread": unread,
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "category": n.category.value if hasattr(n.category, "value") else n.category,
                "severity": n.severity.value if hasattr(n.severity, "value") else n.severity,
                "title": n.title,
                "message": n.message,
                "status": n.status.value if hasattr(n.status, "value") else n.status,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


def mark_notification_read(db: Session, *, notification_id: str) -> dict:
    """Mark a notification as read."""
    notif = update_notification_status(db, uuid.UUID(notification_id), "read")
    if not notif:
        return {"error": "Notificación no encontrada"}
    return {"id": str(notif.id), "status": "read"}


def get_notification_counts(db: Session) -> dict:
    """Get notification count summary."""
    return _get_counts(db)


registry.register(
    ToolDefinition(
        name="list_notifications",
        description="Listar notificaciones recientes con filtros opcionales",
        parameters=[
            ToolParameter(
                "status",
                "string",
                "Filtrar por estado",
                required=False,
                enum=["unread", "read", "acknowledged", "resolved"],
            ),
            ToolParameter(
                "category",
                "string",
                "Filtrar por categoría",
                required=False,
                enum=["business", "system", "security"],
            ),
            ToolParameter("limit", "integer", "Cantidad máxima (default 10)", required=False),
        ],
        category="notifications",
        handler=list_notifications,
    )
)

registry.register(
    ToolDefinition(
        name="mark_notification_read",
        description="Marcar una notificación como leída",
        parameters=[
            ToolParameter("notification_id", "string", "UUID de la notificación"),
        ],
        category="notifications",
        handler=mark_notification_read,
    )
)

registry.register(
    ToolDefinition(
        name="get_notification_counts",
        description="Obtener resumen de conteo de notificaciones (total, por categoría, por severidad)",
        category="notifications",
        handler=get_notification_counts,
    )
)
