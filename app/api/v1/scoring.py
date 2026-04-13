import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.request_context import get_correlation_id
from app.db.session import get_db
from app.schemas.lead import LeadResponse
from app.schemas.operational import RescoreAllStatusResponse, TaskQueuedResponse, TaskStopResponse
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.leads.scoring_service import score_lead
from app.services.pipeline.operational_task_service import (
    RESCORE_ALL_REDIS_KEY,
    RESCORE_ALL_SCOPE_KEY,
    get_rescore_all_task_run,
    load_legacy_operational_state,
    serialize_rescore_all_status,
)
from app.services.pipeline.task_tracking_service import (
    attach_pipeline_root_task,
    create_pipeline_run,
    queue_task_run,
    request_task_stop,
)
from app.workers.pipeline_tasks import task_analyze_lead, task_full_pipeline

router = APIRouter(prefix="/scoring", tags=["scoring"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/rescore-all", response_model=TaskQueuedResponse)
def rescore_all_leads(request: Request, db: DbSession):
    """Re-score all leads. Useful after scoring weight changes."""
    from app.workers.batch_tasks import task_rescore_all

    existing = get_rescore_all_task_run(db)
    if existing and existing.status in {"queued", "running", "retrying", "stopping"}:
        payload = serialize_rescore_all_status(existing)
        return {
            "task_id": existing.task_id,
            "status": payload["status"],
            "message": "Ya hay un rescore-all en curso.",
        }

    legacy = load_legacy_operational_state(RESCORE_ALL_REDIS_KEY)
    if legacy and legacy.get("status") in {"running", "stopping"}:
        return {
            "task_id": str(legacy.get("task_id") or ""),
            "status": legacy["status"],
            "message": "Ya hay un rescore-all en curso.",
        }

    correlation_id = get_correlation_id(request)
    task = task_rescore_all.delay(correlation_id=correlation_id)
    queue_task_run(
        db,
        task_id=str(task.id),
        task_name="task_rescore_all",
        queue="default",
        correlation_id=correlation_id,
        scope_key=RESCORE_ALL_SCOPE_KEY,
        current_step="rescore_dispatch",
    )
    db.commit()
    return {
        "task_id": str(task.id),
        "status": "queued",
        "correlation_id": correlation_id,
    }


@router.get("/rescore-all/status", response_model=RescoreAllStatusResponse)
def get_rescore_all_status(db: DbSession):
    """Return canonical operational state for the latest rescore-all run."""
    task_run = get_rescore_all_task_run(db)
    if task_run:
        return serialize_rescore_all_status(task_run)

    legacy = load_legacy_operational_state(RESCORE_ALL_REDIS_KEY)
    if legacy:
        return legacy
    return {"status": "idle"}


@router.post("/rescore-all/stop", response_model=TaskStopResponse)
def stop_rescore_all(db: DbSession):
    """Signal the active rescore-all task to stop after the current lead."""
    task_run = request_task_stop(
        db,
        task_name="task_rescore_all",
        scope_key=RESCORE_ALL_SCOPE_KEY,
    )
    if task_run:
        db.commit()
        return {"ok": True, "message": "Rescore-all deteniéndose tras el lead actual."}
    return {"ok": True, "message": "No habia rescore-all corriendo."}


@router.post("/{lead_id}", response_model=LeadResponse)
def score(lead_id: uuid.UUID, db: DbSession):
    """Score a lead synchronously based on its signals."""
    lead = score_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/analyze", response_model=TaskEnqueueResponse)
def analyze_with_llm(
    lead_id: uuid.UUID,
    request: Request,
    db: DbSession,
):
    """Queue LLM analysis (summary + quality evaluation) as an async task."""
    correlation_id = get_correlation_id(request)
    task = task_analyze_lead.delay(str(lead_id), correlation_id=correlation_id)
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_analyze_lead",
        queue="llm",
        lead_id=lead_id,
        correlation_id=correlation_id,
        current_step="analysis",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "llm",
        "lead_id": lead_id,
        "current_step": "analysis",
    }


@router.post("/{lead_id}/pipeline", response_model=TaskEnqueueResponse)
def run_full_pipeline(
    lead_id: uuid.UUID,
    request: Request,
    db: DbSession,
):
    """Run the full pipeline: enrich -> score -> LLM analyze -> generate draft."""
    correlation_id = get_correlation_id(request)
    pipeline_run = create_pipeline_run(
        db,
        lead_id,
        current_step="pipeline_dispatch",
        correlation_id=correlation_id,
    )
    task = task_full_pipeline.delay(
        str(lead_id),
        pipeline_run_id=str(pipeline_run.id),
        correlation_id=pipeline_run.correlation_id,
    )
    attach_pipeline_root_task(db, pipeline_run.id, task.id)
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_full_pipeline",
        queue="default",
        lead_id=lead_id,
        pipeline_run_id=pipeline_run.id,
        correlation_id=pipeline_run.correlation_id,
        current_step="pipeline_dispatch",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "default",
        "lead_id": lead_id,
        "pipeline_run_id": pipeline_run.id,
        "current_step": "pipeline_dispatch",
    }
