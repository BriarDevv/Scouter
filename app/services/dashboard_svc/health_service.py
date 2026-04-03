"""Chequeos de salud para cada componente de infraestructura."""

import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _component_result(
    name: str,
    status: str,
    latency_ms: float | None = None,
    error: str | None = None,
) -> dict:
    return {
        "name": name,
        "status": status,
        "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
        "error": error,
    }


def check_database(db: Session) -> dict:
    """Ejecuta SELECT 1 contra la base de datos."""
    try:
        start = time.perf_counter()
        db.execute(text("SELECT 1"))
        elapsed = (time.perf_counter() - start) * 1000
        return _component_result("database", "ok", latency_ms=elapsed)
    except Exception as exc:
        logger.warning("health_check_database_error", error=str(exc))
        return _component_result("database", "error", error=str(exc))


def check_redis() -> dict:
    """Conecta a Redis y ejecuta PING."""
    try:
        import redis

        start = time.perf_counter()
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        client.ping()
        elapsed = (time.perf_counter() - start) * 1000
        client.close()
        return _component_result("redis", "ok", latency_ms=elapsed)
    except Exception as exc:
        logger.warning("health_check_redis_error", error=str(exc))
        return _component_result("redis", "error", error=str(exc))


def check_ollama() -> dict:
    """HTTP GET a Ollama /api/tags para verificar disponibilidad."""
    try:
        start = time.perf_counter()
        resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        elapsed = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            return _component_result("ollama", "ok", latency_ms=elapsed)
        return _component_result(
            "ollama", "error", latency_ms=elapsed, error=f"HTTP {resp.status_code}"
        )
    except Exception as exc:
        logger.warning("health_check_ollama_error", error=str(exc))
        return _component_result("ollama", "error", error=str(exc))


def check_celery() -> dict:
    """Intenta hacer inspect.ping() al worker de Celery."""
    try:
        from app.workers.celery_app import celery_app

        start = time.perf_counter()
        inspector = celery_app.control.inspect(timeout=3)
        ping_result = inspector.ping()
        elapsed = (time.perf_counter() - start) * 1000

        if ping_result:
            return _component_result("celery", "ok", latency_ms=elapsed)
        return _component_result(
            "celery", "degraded", latency_ms=elapsed, error="Sin workers activos"
        )
    except ImportError:
        return _component_result("celery", "degraded", error="Celery no disponible")
    except Exception as exc:
        logger.warning("health_check_celery_error", error=str(exc))
        return _component_result("celery", "error", error=str(exc))


def get_system_health(db: Session | None = None) -> dict:
    """Ejecuta todos los chequeos y retorna el estado agregado."""
    components: list[dict] = []

    if db is not None:
        components.append(check_database(db))
    else:
        components.append(_component_result("database", "error", error="Sesión no disponible"))

    components.append(check_redis())
    components.append(check_ollama())
    components.append(check_celery())

    statuses = [c["status"] for c in components]
    all_ok = all(s == "ok" for s in statuses)
    all_error = all(s == "error" for s in statuses)

    if all_ok:
        overall = "healthy"
    elif all_error:
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "components": components,
        "checked_at": datetime.now(UTC).isoformat(),
    }
