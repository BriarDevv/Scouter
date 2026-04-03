"""Crawl tools — start territory crawls and check status."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.core.config import settings as env
from app.services.pipeline.operational_task_service import (
    get_territory_crawl_status_snapshot,
    get_territory_crawl_task_run,
    load_territory_crawl_legacy_status,
)
from app.services.pipeline.task_tracking_service import queue_task_run


def start_territory_crawl(
    db: Session, *, territory_id: str, max_results: int = 20
) -> dict:
    """Launch a territory crawl via Celery."""
    try:
        tid = uuid.UUID(territory_id)
    except ValueError:
        return {"error": "ID de territorio inválido (debe ser UUID)"}

    if not env.GOOGLE_MAPS_API_KEY:
        return {"error": "Google Maps API key no configurada"}

    from app.models.territory import Territory

    territory = db.get(Territory, tid)
    if not territory:
        return {"error": "Territorio no encontrado"}

    existing = get_territory_crawl_task_run(db, territory_id)
    if existing and existing.status in {"queued", "running", "retrying", "stopping"}:
        return {
            "status": "already_running",
            "territory_name": territory.name,
            "progress": get_territory_crawl_status_snapshot(db, territory_id),
        }

    legacy = load_territory_crawl_legacy_status(territory_id)
    if legacy.get("status") in {"running", "stopping"}:
        return {
            "status": "already_running",
            "territory_name": territory.name,
            "progress": legacy,
        }

    from app.workers.tasks import task_crawl_territory

    correlation_id = str(uuid.uuid4())
    task = task_crawl_territory.delay(
        territory_id=territory_id,
        max_results_per_category=max_results,
        correlation_id=correlation_id,
    )
    queue_task_run(
        db,
        task_id=str(task.id),
        task_name="task_crawl_territory",
        queue="default",
        correlation_id=correlation_id,
        scope_key=territory_id,
        current_step="crawl_dispatch",
    )

    return {
        "status": "started",
        "territory_name": territory.name,
        "task_id": str(task.id),
    }


def get_crawl_status(db: Session, *, territory_id: str) -> dict:
    """Check the crawl progress for a territory."""
    return get_territory_crawl_status_snapshot(db, territory_id)


registry.register(ToolDefinition(
    name="start_territory_crawl",
    description=(
        "Iniciar un crawl de Google Maps para un territorio "
        "(requiere confirmación — lanza tarea asíncrona y consume API key)"
    ),
    parameters=[
        ToolParameter("territory_id", "string", "UUID del territorio"),
        ToolParameter(
            "max_results", "integer",
            "Máximo de resultados por categoría (default 20)",
            required=False,
        ),
    ],
    category="crawl",
    requires_confirmation=True,
    handler=start_territory_crawl,
))

registry.register(ToolDefinition(
    name="get_crawl_status",
    description="Consultar el progreso de un crawl de territorio en curso",
    parameters=[
        ToolParameter("territory_id", "string", "UUID del territorio"),
    ],
    category="crawl",
    handler=get_crawl_status,
))
