"""Leader tools — rich system overview and top leads."""

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.dashboard_svc.leader_service import (
    get_reply_summary as _reply_summary,
    get_system_overview as _overview,
    list_recent_activity_items as _recent_activity,
    list_top_leads as _top_leads,
)


def get_system_overview(db: Session) -> dict:
    """Get a comprehensive system overview with stats and highlights."""
    data = _overview(db)
    # Serialize datetime for JSON
    if "snapshot_at" in data:
        data["snapshot_at"] = str(data["snapshot_at"])
    return data


def list_top_leads(db: Session, *, limit: int = 10) -> dict:
    """List the highest-scoring leads."""
    leads = _top_leads(db, limit=min(limit, 20))
    for lead in leads:
        for key in ("created_at", "updated_at", "enriched_at", "scored_at"):
            if key in lead and lead[key] is not None:
                lead[key] = str(lead[key])
    return {"count": len(leads), "leads": leads}


def get_reply_summary(db: Session, *, hours: int = 24) -> dict:
    """Get summary of inbound replies in the last N hours."""
    data = _reply_summary(db, hours=min(hours, 168))
    for key in ("since_at", "snapshot_at", "latest_reply_at"):
        if key in data and data[key] is not None:
            data[key] = str(data[key])
    return data


def list_recent_activity(db: Session, *, limit: int = 10) -> dict:
    """List recent system activity (outreach logs)."""
    items = _recent_activity(db, limit=min(limit, 30))
    for item in items:
        for key in ("id", "lead_id", "draft_id"):
            if key in item and item[key] is not None:
                item[key] = str(item[key])
        if "created_at" in item and item["created_at"] is not None:
            item["created_at"] = str(item["created_at"])
        if "action" in item and hasattr(item["action"], "value"):
            item["action"] = item["action"].value
    return {"count": len(items), "items": items}


registry.register(ToolDefinition(
    name="get_system_overview",
    description=(
        "Obtener un resumen ejecutivo completo del sistema: leads, drafts, "
        "pipelines, tareas, actividad reciente y highlights de rendimiento"
    ),
    category="stats",
    handler=get_system_overview,
))

registry.register(ToolDefinition(
    name="list_top_leads",
    description="Listar los leads con mayor score y potencial",
    parameters=[
        ToolParameter("limit", "integer", "Cantidad (default 10)", required=False),
    ],
    category="leads",
    handler=list_top_leads,
))

registry.register(ToolDefinition(
    name="get_reply_summary",
    description="Resumen de replies inbound recientes (últimas N horas)",
    parameters=[
        ToolParameter("hours", "integer", "Ventana de horas (default 24)", required=False),
    ],
    category="stats",
    handler=get_reply_summary,
))

registry.register(ToolDefinition(
    name="list_recent_activity",
    description="Últimas acciones del sistema (outreach logs, actividad reciente)",
    parameters=[
        ToolParameter("limit", "integer", "Cantidad (default 10)", required=False),
    ],
    category="stats",
    handler=list_recent_activity,
))
