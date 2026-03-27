"""Crawl endpoints: trigger Google Maps discovery and ingest leads."""

import json as _json

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from redis import Redis

from app.api.deps import get_session
from app.core.config import settings as env
from app.crawlers.google_maps_crawler import DEFAULT_CATEGORIES

router = APIRouter(prefix="/crawl", tags=["crawl"])


# ── Territory-based crawl (async via Celery) ──────────────────────────

class TerritoryCrawlRequest(BaseModel):
    territory_id: str
    categories: list[str] | None = None
    only_without_website: bool = False
    max_results_per_category: int = 20


@router.post("/territory")
def start_territory_crawl(body: TerritoryCrawlRequest, db=Depends(get_session)):
    """Start a crawl for all cities in a territory (async via Celery)."""
    if not env.GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=400, detail="Google Maps API key no configurada.")

    # Verify territory exists
    from app.models.territory import Territory
    import uuid
    territory = db.get(Territory, uuid.UUID(body.territory_id))
    if not territory:
        raise HTTPException(status_code=404, detail="Territorio no encontrado.")

    # Check if a crawl is already running for this territory
    redis = Redis.from_url(env.REDIS_URL)
    redis_key = f"crawl:territory:{body.territory_id}"
    existing = redis.get(redis_key)
    if existing:
        data = _json.loads(existing)
        if data.get("status") == "running":
            return {"ok": False, "message": "Ya hay un crawl en curso para este territorio.", "progress": data}

    # Launch Celery task
    from app.workers.tasks import task_crawl_territory
    result = task_crawl_territory.delay(
        territory_id=body.territory_id,
        categories=body.categories,
        only_without_website=body.only_without_website,
        max_results_per_category=body.max_results_per_category,
    )

    # Store task_id in Redis so frontend can revoke it after reload
    redis.set(redis_key, _json.dumps({"status": "running", "task_id": str(result.id), "territory": territory.name}), ex=3600)

    return {"ok": True, "task_id": str(result.id), "message": f"Crawl iniciado para {territory.name} ({len(territory.cities)} ciudades)."}


@router.get("/territory/{territory_id}/status")
def get_territory_crawl_status(territory_id: str):
    """Poll crawl progress for a territory."""
    redis = Redis.from_url(env.REDIS_URL)
    redis_key = f"crawl:territory:{territory_id}"
    data = redis.get(redis_key)
    if not data:
        return {"status": "idle"}
    return _json.loads(data)


@router.post("/territory/{territory_id}/stop")
def stop_territory_crawl(territory_id: str):
    """Signal the crawl to stop after the current city."""
    redis = Redis.from_url(env.REDIS_URL)
    redis_key = f"crawl:territory:{territory_id}"
    existing = redis.get(redis_key)
    if existing:
        data = _json.loads(existing)
        if data.get("status") in ("running", "stopping"):
            data["status"] = "stopping"
            redis.set(redis_key, _json.dumps(data), ex=3600)
            return {"ok": True, "message": "Crawl deteniéndose tras la ciudad actual."}
    redis.delete(redis_key)
    return {"ok": True, "message": "No habia crawl corriendo."}


# ── Categories ────────────────────────────────────────────────────────

@router.get("/categories")
def get_categories():
    """Return the default crawl categories."""
    return {"categories": DEFAULT_CATEGORIES}


# ── API Key management ────────────────────────────────────────────────

@router.get("/api-key-status")
def api_key_status():
    """Check if Google Maps API key is configured."""
    key = env.GOOGLE_MAPS_API_KEY
    return {
        "configured": bool(key),
        "masked": f"{key[:10]}...{key[-4:]}" if key and len(key) > 14 else None,
    }


class ApiKeyUpdate(BaseModel):
    api_key: str


@router.patch("/api-key")
def update_api_key(body: ApiKeyUpdate):
    """Update the Google Maps API key in .env file."""
    from pathlib import Path
    import re

    env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if not env_path.exists():
        raise HTTPException(status_code=404, detail=".env file not found")

    content = env_path.read_text()
    new_key = body.api_key.strip()

    if "GOOGLE_MAPS_API_KEY" in content:
        content = re.sub(
            r"GOOGLE_MAPS_API_KEY=.*",
            f"GOOGLE_MAPS_API_KEY={new_key}",
            content,
        )
    else:
        content = content.rstrip() + f"\nGOOGLE_MAPS_API_KEY={new_key}\n"

    env_path.write_text(content)
    env.GOOGLE_MAPS_API_KEY = new_key

    return {
        "ok": True,
        "configured": True,
        "masked": f"{new_key[:10]}...{new_key[-4:]}" if len(new_key) > 14 else new_key,
    }
