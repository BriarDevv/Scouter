"""Crawl endpoints: trigger Google Maps discovery and ingest leads."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.request_context import get_correlation_id
from app.crawlers.google_maps_crawler import DEFAULT_CATEGORIES
from app.db.session import get_db
from app.services.deploy.deploy_config_service import (
    InvalidGoogleMapsKeyError,
    clear_google_maps_api_key,
    get_effective_google_maps_key,
    get_google_maps_api_key_status,
    set_google_maps_api_key,
)
from app.services.pipeline.operational_task_service import (
    get_territory_crawl_status_snapshot,
    get_territory_crawl_task_run,
    load_territory_crawl_legacy_status,
    mark_territory_crawl_legacy_stop_requested,
)
from app.services.pipeline.task_tracking_service import queue_task_run, request_task_stop

router = APIRouter(prefix="/crawl", tags=["crawl"])
DbSession = Annotated[Session, Depends(get_db)]


# ── Territory-based crawl (async via Celery) ──────────────────────────


class TerritoryCrawlRequest(BaseModel):
    territory_id: str
    categories: list[str] | None = None
    only_without_website: bool = False
    max_results_per_category: int = 20


@router.post("/territory")
def start_territory_crawl(
    body: TerritoryCrawlRequest,
    request: Request,
    db: DbSession,
):
    """Start a crawl for all cities in a territory (async via Celery)."""
    if not get_effective_google_maps_key(db):
        raise HTTPException(
            status_code=400,
            detail=(
                "Google Maps API key no configurada. Cargala en Configuración → "
                "Crawlers o definí GOOGLE_MAPS_API_KEY en el .env."
            ),
        )

    # Verify territory exists
    import uuid

    from app.models.territory import Territory

    territory = db.get(Territory, uuid.UUID(body.territory_id))
    if not territory:
        raise HTTPException(status_code=404, detail="Territorio no encontrado.")

    # Check canonical tracked state first, then fall back to legacy cached state.
    existing_task = get_territory_crawl_task_run(db, body.territory_id)
    if existing_task and existing_task.status in {"queued", "running", "retrying", "stopping"}:
        return {
            "ok": False,
            "message": "Ya hay un crawl en curso para este territorio.",
            "progress": get_territory_crawl_status_snapshot(db, body.territory_id),
        }

    legacy = load_territory_crawl_legacy_status(body.territory_id)
    if legacy.get("status") in {"running", "stopping"}:
        return {
            "ok": False,
            "message": "Ya hay un crawl en curso para este territorio.",
            "progress": legacy,
        }

    # Launch Celery task
    from app.workers.crawl_tasks import task_crawl_territory

    correlation_id = get_correlation_id(request)
    result = task_crawl_territory.delay(
        territory_id=body.territory_id,
        categories=body.categories,
        only_without_website=body.only_without_website,
        max_results_per_category=body.max_results_per_category,
        correlation_id=correlation_id,
    )

    queue_task_run(
        db,
        task_id=str(result.id),
        task_name="task_crawl_territory",
        queue="default",
        correlation_id=correlation_id,
        scope_key=body.territory_id,
        current_step="crawl_dispatch",
    )
    db.commit()

    return {
        "ok": True,
        "task_id": str(result.id),
        "correlation_id": correlation_id,
        "message": (f"Crawl iniciado para {territory.name} ({len(territory.cities)} ciudades)."),
    }


@router.get("/territory/{territory_id}/status")
def get_territory_crawl_status(territory_id: str, db: DbSession):
    """Poll crawl progress for a territory."""
    return get_territory_crawl_status_snapshot(db, territory_id)


@router.post("/territory/{territory_id}/stop")
def stop_territory_crawl(territory_id: str, db: DbSession):
    """Signal the crawl to stop after the current city."""
    task_run = request_task_stop(
        db,
        task_name="task_crawl_territory",
        scope_key=territory_id,
    )
    if task_run:
        db.commit()
        return {"ok": True, "message": "Crawl deteniéndose tras la ciudad actual."}

    if mark_territory_crawl_legacy_stop_requested(territory_id):
        return {"ok": True, "message": "Crawl deteniéndose tras la ciudad actual."}
    return {"ok": True, "message": "No habia crawl corriendo."}


# ── Categories ────────────────────────────────────────────────────────


@router.get("/categories")
def get_categories():
    """Return the default crawl categories."""
    return {"categories": DEFAULT_CATEGORIES}


# ── API Key management ────────────────────────────────────────────────


@router.get("/api-key-status")
def api_key_status(db: DbSession):
    """Report whether the Google Maps API key is set and where it lives (db|env)."""
    return get_google_maps_api_key_status(db)


class ApiKeyUpdate(BaseModel):
    api_key: str


@router.patch("/api-key")
def update_api_key(body: ApiKeyUpdate, db: DbSession):
    """Persist a Google Maps API key in integration_credentials (encrypted).

    DB value wins over the .env fallback. The operator can replace or clear
    the key at any time without restarting the backend.
    """
    try:
        status = set_google_maps_api_key(db, body.api_key)
    except InvalidGoogleMapsKeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return status


@router.delete("/api-key")
def delete_api_key(db: DbSession):
    """Clear the DB-stored Google Maps API key (env fallback still applies)."""
    status = clear_google_maps_api_key(db)
    db.commit()
    return status
