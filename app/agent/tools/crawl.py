"""Crawl tools — start territory crawls and check status."""

import json as _json
import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.core.config import settings as env


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

    from redis import Redis

    redis = Redis.from_url(env.REDIS_URL)
    redis_key = f"crawl:territory:{territory_id}"
    existing = redis.get(redis_key)
    if existing:
        data = _json.loads(existing)
        if data.get("status") == "running":
            return {
                "status": "already_running",
                "territory_name": territory.name,
            }

    from app.workers.tasks import task_crawl_territory

    task_crawl_territory.delay(
        territory_id=territory_id,
        max_results_per_category=max_results,
    )

    redis.set(
        redis_key,
        _json.dumps({
            "status": "running",
            "territory": territory.name,
        }),
        ex=3600,
    )

    return {
        "status": "started",
        "territory_name": territory.name,
    }


def get_crawl_status(db: Session, *, territory_id: str) -> dict:
    """Check the crawl progress for a territory."""
    from redis import Redis

    redis = Redis.from_url(env.REDIS_URL)
    redis_key = f"crawl:territory:{territory_id}"
    data = redis.get(redis_key)
    if not data:
        return {"status": "idle"}
    return _json.loads(data)


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
