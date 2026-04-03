import json as _json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.request_context import get_correlation_id
from app.core.config import settings as env
from app.schemas.task_tracking import (
    PipelineRunDetailResponse,
    PipelineRunSummaryResponse,
    TaskStatusResponse,
)
from app.services.operational_task_service import (
    BATCH_PIPELINE_SCOPE_KEY,
    get_batch_pipeline_task_run,
    serialize_batch_pipeline_status,
)
from app.services.task_tracking_service import (
    get_pipeline_run,
    list_pipeline_runs,
    list_task_runs,
    queue_task_run,
    request_task_stop,
)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("/runs", response_model=list[PipelineRunSummaryResponse])
def list_runs(
    lead_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """List recent pipeline runs to inspect active and failed flows."""
    return list_pipeline_runs(db, lead_id=lead_id, status=status, limit=limit)


@router.get("/runs/{pipeline_run_id}", response_model=PipelineRunDetailResponse)
def get_run(pipeline_run_id: uuid.UUID, db: Session = Depends(get_session)):
    """Return a pipeline run plus the tracked tasks that belong to it."""
    run = get_pipeline_run(db, pipeline_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    tasks = [
        TaskStatusResponse(
            task_id=task.task_id,
            status=task.status,
            queue=task.queue,
            lead_id=task.lead_id,
            pipeline_run_id=task.pipeline_run_id,
            current_step=task.current_step,
            correlation_id=task.correlation_id,
            result=task.result,
            error=task.error,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            finished_at=task.finished_at,
        )
        for task in list_task_runs(db, pipeline_run_id=pipeline_run_id, limit=100)
    ]

    return PipelineRunDetailResponse(
        id=run.id,
        lead_id=run.lead_id,
        correlation_id=run.correlation_id,
        root_task_id=run.root_task_id,
        status=run.status,
        current_step=run.current_step,
        result=run.result,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        tasks=tasks,
    )


# ── Batch pipeline (process all new leads) ──────────────────────────

def _legacy_batch_pipeline_status() -> dict:
    try:
        redis = Redis.from_url(env.REDIS_URL)
        data = redis.get("pipeline:batch")
    except Exception:
        return {"status": "idle"}
    if not data:
        return {"status": "idle"}
    return _json.loads(data)


@router.post("/batch")
def start_batch_pipeline(request: Request, db: Session = Depends(get_session)):
    """Start the batch pipeline that processes all 'new' leads."""
    existing = get_batch_pipeline_task_run(db)
    if existing and existing.status in {"queued", "running", "retrying", "stopping"}:
        return {
            "ok": False,
            "message": "El pipeline batch ya esta corriendo.",
            "progress": serialize_batch_pipeline_status(existing),
        }

    legacy = _legacy_batch_pipeline_status()
    if legacy.get("status") in {"running", "stopping"}:
        return {
            "ok": False,
            "message": "El pipeline batch ya esta corriendo.",
            "progress": legacy,
        }

    from app.workers.tasks import task_batch_pipeline
    correlation_id = get_correlation_id(request)
    result = task_batch_pipeline.delay(
        status_filter="new",
        correlation_id=correlation_id,
    )

    queue_task_run(
        db,
        task_id=str(result.id),
        task_name="task_batch_pipeline",
        queue="default",
        correlation_id=correlation_id,
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        current_step="batch_dispatch",
    )

    return {
        "ok": True,
        "task_id": str(result.id),
        "message": "Pipeline batch iniciado.",
        "correlation_id": correlation_id,
    }


@router.get("/batch/status")
def get_batch_pipeline_status(db: Session = Depends(get_session)):
    """Poll batch pipeline progress."""
    task_run = get_batch_pipeline_task_run(db)
    if task_run:
        return serialize_batch_pipeline_status(task_run)
    return _legacy_batch_pipeline_status()


@router.post("/batch/stop")
def stop_batch_pipeline(db: Session = Depends(get_session)):
    """Signal the batch pipeline to stop after the current lead."""
    task_run = request_task_stop(
        db,
        task_name="task_batch_pipeline",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
    )
    if task_run:
        return {"ok": True, "message": "Pipeline batch deteniéndose tras el lead actual."}

    try:
        redis = Redis.from_url(env.REDIS_URL)
        redis_key = "pipeline:batch"
        existing = redis.get(redis_key)
    except Exception:
        return {"ok": True, "message": "No habia pipeline corriendo."}
    if existing:
        data = _json.loads(existing)
        if data.get("status") in ("running", "stopping"):
            data["status"] = "stopping"
            redis.set(redis_key, _json.dumps(data), ex=3600)
            return {"ok": True, "message": "Pipeline batch deteniéndose tras el lead actual."}
    redis.delete(redis_key)
    return {"ok": True, "message": "No habia pipeline corriendo."}
