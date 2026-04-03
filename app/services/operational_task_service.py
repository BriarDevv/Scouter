"""Helpers for canonical operator-facing workflow state backed by TaskRun."""

from __future__ import annotations

import json as _json

from redis import Redis

from app.core.config import settings as env
from app.models.task_tracking import TaskRun
from app.services.task_tracking_service import get_scoped_task_run

BATCH_PIPELINE_SCOPE_KEY = "status:new"
RESCORE_ALL_SCOPE_KEY = "scores:all"
RESCORE_ALL_REDIS_KEY = "pipeline:rescore"
DEFAULT_LEGACY_MIRROR_TTL_SECONDS = 3600


def _serialize_status(status: str, *, stop_requested: bool) -> str:
    if status == "stopped":
        return "stopped"
    if status == "failed":
        return "error"
    if status == "succeeded":
        return "done"
    if status == "stopping" or stop_requested:
        return "stopping"
    if status in {"queued", "running", "retrying"}:
        return "running"
    return status


def get_batch_pipeline_task_run(db) -> TaskRun | None:
    task_run = get_scoped_task_run(
        db,
        task_name="task_batch_pipeline",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        active_only=True,
    )
    if task_run:
        return task_run
    return get_scoped_task_run(
        db,
        task_name="task_batch_pipeline",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        active_only=False,
    )


def get_territory_crawl_task_run(db, territory_id: str) -> TaskRun | None:
    task_run = get_scoped_task_run(
        db,
        task_name="task_crawl_territory",
        scope_key=territory_id,
        active_only=True,
    )
    if task_run:
        return task_run
    return get_scoped_task_run(
        db,
        task_name="task_crawl_territory",
        scope_key=territory_id,
        active_only=False,
    )


def get_rescore_all_task_run(db) -> TaskRun | None:
    task_run = get_scoped_task_run(
        db,
        task_name="task_rescore_all",
        scope_key=RESCORE_ALL_SCOPE_KEY,
        active_only=True,
    )
    if task_run:
        return task_run
    return get_scoped_task_run(
        db,
        task_name="task_rescore_all",
        scope_key=RESCORE_ALL_SCOPE_KEY,
        active_only=False,
    )


def serialize_batch_pipeline_status(task_run: TaskRun | None) -> dict:
    if not task_run:
        return {"status": "idle"}

    progress = dict(task_run.progress_json or {})
    return {
        "status": _serialize_status(
            task_run.status,
            stop_requested=task_run.stop_requested_at is not None,
        ),
        "task_id": task_run.task_id,
        "total": progress.get("total", 0),
        "processed": progress.get("processed", 0),
        "current_lead": progress.get("current_lead"),
        "current_step": task_run.current_step or progress.get("current_step"),
        "errors": progress.get("errors", 0),
        "crawl_rounds": progress.get("crawl_rounds", 0),
        "leads_from_crawl": progress.get("leads_from_crawl", 0),
        "error": task_run.error,
        "correlation_id": task_run.correlation_id,
    }


def serialize_territory_crawl_status(task_run: TaskRun | None) -> dict:
    if not task_run:
        return {"status": "idle"}

    progress = dict(task_run.progress_json or {})
    return {
        "status": _serialize_status(
            task_run.status,
            stop_requested=task_run.stop_requested_at is not None,
        ),
        "task_id": task_run.task_id,
        "territory": progress.get("territory"),
        "total_cities": progress.get("total_cities"),
        "current_city_idx": progress.get("current_city_idx"),
        "current_city": progress.get("current_city"),
        "leads_found": progress.get("leads_found", 0),
        "leads_created": progress.get("leads_created", 0),
        "leads_skipped": progress.get("leads_skipped", 0),
        "error": task_run.error,
        "correlation_id": task_run.correlation_id,
    }


def build_rescore_all_progress(
    *,
    total: int,
    rescored: int,
    errors: int,
    current_lead_id: str | None = None,
) -> dict:
    return {
        "total": total,
        "rescored": rescored,
        "errors": errors,
        "current_lead_id": current_lead_id,
    }


def serialize_rescore_all_status(task_run: TaskRun | None) -> dict:
    if not task_run:
        return {"status": "idle"}

    progress = dict(task_run.progress_json or {})
    return {
        "status": _serialize_status(
            task_run.status,
            stop_requested=task_run.stop_requested_at is not None,
        ),
        "task_id": task_run.task_id,
        "total": progress.get("total", 0),
        "rescored": progress.get("rescored", 0),
        "errors": progress.get("errors", 0),
        "current_lead_id": progress.get("current_lead_id"),
        "current_step": task_run.current_step or progress.get("current_step"),
        "error": task_run.error,
        "correlation_id": task_run.correlation_id,
    }


def load_legacy_operational_state(redis_key: str) -> dict | None:
    try:
        redis = Redis.from_url(env.REDIS_URL)
        payload = redis.get(redis_key)
    except Exception:
        return None
    if not payload:
        return None
    return _json.loads(payload)


def mirror_legacy_operational_state(
    redis_key: str,
    payload: dict,
    *,
    ttl_seconds: int = DEFAULT_LEGACY_MIRROR_TTL_SECONDS,
) -> None:
    try:
        redis = Redis.from_url(env.REDIS_URL)
        redis.set(redis_key, _json.dumps(payload), ex=ttl_seconds)
    except Exception:
        return
