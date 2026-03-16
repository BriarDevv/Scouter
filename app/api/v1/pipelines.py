import json as _json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from redis import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import settings as env
from app.schemas.task_tracking import PipelineRunDetailResponse, PipelineRunSummaryResponse, TaskStatusResponse
from app.services.task_tracking_service import get_pipeline_run, list_pipeline_runs, list_task_runs

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

@router.post("/batch")
def start_batch_pipeline():
    """Start the batch pipeline that processes all 'new' leads."""
    redis = Redis.from_url(env.REDIS_URL)
    redis_key = "pipeline:batch"

    # Check if already running
    existing = redis.get(redis_key)
    if existing:
        data = _json.loads(existing)
        if data.get("status") == "running":
            return {"ok": False, "message": "El pipeline batch ya esta corriendo.", "progress": data}

    from app.workers.tasks import task_batch_pipeline
    result = task_batch_pipeline.delay()

    redis.set(redis_key, _json.dumps({"status": "running", "task_id": str(result.id)}), ex=7200)
    return {"ok": True, "task_id": str(result.id), "message": "Pipeline batch iniciado."}


@router.get("/batch/status")
def get_batch_pipeline_status():
    """Poll batch pipeline progress."""
    redis = Redis.from_url(env.REDIS_URL)
    data = redis.get("pipeline:batch")
    if not data:
        return {"status": "idle"}
    return _json.loads(data)


@router.post("/batch/stop")
def stop_batch_pipeline():
    """Signal the batch pipeline to stop after the current lead."""
    redis = Redis.from_url(env.REDIS_URL)
    redis_key = "pipeline:batch"
    existing = redis.get(redis_key)
    if existing:
        data = _json.loads(existing)
        if data.get("status") == "running":
            data["status"] = "stopping"
            redis.set(redis_key, _json.dumps(data), ex=7200)
            # Also revoke the Celery task
            if data.get("task_id"):
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(data["task_id"], terminate=True, signal="SIGTERM")
            return {"ok": True, "message": "Pipeline batch detenido."}
    redis.delete(redis_key)
    return {"ok": True, "message": "No habia pipeline corriendo."}
