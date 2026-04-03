"""Helpers for canonical operator-facing workflow state backed by TaskRun."""

from __future__ import annotations

import json as _json

from redis import Redis

from app.core.config import settings as env
from app.db.session import SessionLocal
from app.models.task_tracking import TaskRun
from app.services.task_tracking_service import (
    get_scoped_task_run,
    is_task_stop_requested,
    update_task_run,
)

BATCH_PIPELINE_SCOPE_KEY = "status:new"
BATCH_PIPELINE_REDIS_KEY = "pipeline:batch"
RESCORE_ALL_SCOPE_KEY = "scores:all"
RESCORE_ALL_REDIS_KEY = "pipeline:rescore"
TERRITORY_CRAWL_REDIS_PREFIX = "crawl:territory:"
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


def territory_crawl_redis_key(territory_id: str) -> str:
    return f"{TERRITORY_CRAWL_REDIS_PREFIX}{territory_id}"


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


def build_batch_pipeline_progress(
    *,
    task_id: str,
    status: str = "running",
    total: int = 0,
    processed: int = 0,
    current_lead: str | None = None,
    current_step: str = "",
    errors: int = 0,
    crawl_rounds: int = 0,
    leads_from_crawl: int = 0,
) -> dict:
    return {
        "status": status,
        "task_id": task_id,
        "total": total,
        "processed": processed,
        "current_lead": current_lead,
        "current_step": current_step,
        "errors": errors,
        "crawl_rounds": crawl_rounds,
        "leads_from_crawl": leads_from_crawl,
    }


def build_territory_crawl_progress(
    *,
    task_id: str,
    status: str = "running",
    territory: str | None = None,
    total_cities: int = 0,
    current_city_idx: int = 0,
    current_city: str = "",
    current_step: str = "",
    leads_found: int = 0,
    leads_created: int = 0,
    leads_skipped: int = 0,
) -> dict:
    return {
        "status": status,
        "task_id": task_id,
        "territory": territory,
        "total_cities": total_cities,
        "current_city_idx": current_city_idx,
        "current_city": current_city,
        "current_step": current_step,
        "leads_found": leads_found,
        "leads_created": leads_created,
        "leads_skipped": leads_skipped,
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


def build_rescore_all_status_payload(
    *,
    status: str,
    task_id: str,
    total: int,
    rescored: int,
    errors: int,
    current_step: str | None = None,
    error: str | None = None,
) -> dict:
    payload = {
        "status": status,
        "task_id": task_id,
        "total": total,
        "rescored": rescored,
        "errors": errors,
    }
    if current_step is not None:
        payload["current_step"] = current_step
    if error is not None:
        payload["error"] = error
    return payload


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


def _read_legacy_operational_state(
    redis_key: str,
    *,
    suppress_errors: bool,
) -> dict | None:
    try:
        redis = Redis.from_url(env.REDIS_URL)
        payload = redis.get(redis_key)
    except Exception:
        if suppress_errors:
            return None
        raise
    if not payload:
        return None
    return _json.loads(payload)


def load_legacy_operational_state(redis_key: str) -> dict | None:
    return _read_legacy_operational_state(redis_key, suppress_errors=True)


def load_legacy_operational_state_or_idle(redis_key: str) -> dict:
    return load_legacy_operational_state(redis_key) or {"status": "idle"}


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


def delete_legacy_operational_state(redis_key: str) -> None:
    try:
        redis = Redis.from_url(env.REDIS_URL)
        redis.delete(redis_key)
    except Exception:
        return


def mark_legacy_operational_stop_requested(redis_key: str) -> bool:
    payload = load_legacy_operational_state(redis_key)
    if not payload:
        delete_legacy_operational_state(redis_key)
        return False
    if payload.get("status") not in {"running", "stopping"}:
        delete_legacy_operational_state(redis_key)
        return False
    payload["status"] = "stopping"
    mirror_legacy_operational_state(redis_key, payload)
    return True


def should_stop_operational_task(
    *,
    task_id: str,
    redis_key: str,
    treat_missing_legacy_as_stop: bool = False,
) -> bool:
    with SessionLocal() as db:
        if is_task_stop_requested(db, task_id):
            return True

    try:
        payload = _read_legacy_operational_state(redis_key, suppress_errors=False)
    except Exception:
        return False
    if payload is None:
        return treat_missing_legacy_as_stop
    return payload.get("status") == "stopping"


def persist_operational_task_state(
    task_id: str,
    *,
    current_step: str | None,
    progress_json: dict,
    status: str | None = None,
    error: str | None = None,
    clear_error: bool = False,
    finished: bool = False,
    result: dict | None = None,
    stop_requested: bool | None = None,
) -> None:
    with SessionLocal() as db:
        update_task_run(
            db,
            task_id,
            status=status,
            current_step=current_step,
            progress_json=progress_json,
            result=result,
            error=error,
            clear_error=clear_error,
            finished=finished,
            stop_requested=stop_requested,
        )


def mirror_batch_pipeline_state(payload: dict) -> None:
    mirror_legacy_operational_state(BATCH_PIPELINE_REDIS_KEY, payload)


def load_batch_pipeline_legacy_status() -> dict:
    return load_legacy_operational_state_or_idle(BATCH_PIPELINE_REDIS_KEY)


def get_batch_pipeline_status_snapshot(db) -> dict:
    task_run = get_batch_pipeline_task_run(db)
    if task_run:
        return serialize_batch_pipeline_status(task_run)
    return load_batch_pipeline_legacy_status()


def mark_batch_pipeline_legacy_stop_requested() -> bool:
    return mark_legacy_operational_stop_requested(BATCH_PIPELINE_REDIS_KEY)


def mirror_rescore_all_state(payload: dict) -> None:
    mirror_legacy_operational_state(RESCORE_ALL_REDIS_KEY, payload)


def persist_rescore_all_state(
    task_id: str,
    *,
    current_step: str | None,
    total: int,
    rescored: int,
    errors: int,
    current_lead_id: str | None = None,
    status: str | None = None,
    error: str | None = None,
    clear_error: bool = False,
    finished: bool = False,
    result: dict | None = None,
    stop_requested: bool | None = None,
) -> None:
    progress = build_rescore_all_progress(
        total=total,
        rescored=rescored,
        errors=errors,
        current_lead_id=current_lead_id,
    )
    persist_operational_task_state(
        task_id,
        current_step=current_step,
        progress_json=progress,
        status=status,
        error=error,
        clear_error=clear_error,
        finished=finished,
        result=result,
        stop_requested=stop_requested,
    )


def mirror_territory_crawl_state(territory_id: str, payload: dict) -> None:
    mirror_legacy_operational_state(territory_crawl_redis_key(territory_id), payload)


def load_territory_crawl_legacy_status(territory_id: str) -> dict:
    return load_legacy_operational_state_or_idle(territory_crawl_redis_key(territory_id))


def get_territory_crawl_status_snapshot(db, territory_id: str) -> dict:
    task_run = get_territory_crawl_task_run(db, territory_id)
    if task_run:
        return serialize_territory_crawl_status(task_run)
    return load_territory_crawl_legacy_status(territory_id)


def mark_territory_crawl_legacy_stop_requested(territory_id: str) -> bool:
    return mark_legacy_operational_stop_requested(territory_crawl_redis_key(territory_id))
