import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.request_context import get_correlation_id
from app.schemas.task_tracking import (
    PipelineRunDetailResponse,
    PipelineRunSummaryResponse,
    TaskStatusResponse,
)
from app.services.pipeline.operational_task_service import (
    BATCH_PIPELINE_SCOPE_KEY,
    get_batch_pipeline_status_snapshot,
    get_batch_pipeline_task_run,
    load_batch_pipeline_legacy_status,
    mark_batch_pipeline_legacy_stop_requested,
)
from app.services.pipeline.task_tracking_service import (
    get_pipeline_run,
    list_pipeline_runs,
    list_task_runs,
    queue_task_run,
    request_task_stop,
)

router = APIRouter(prefix="/pipelines", tags=["pipelines"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/runs", response_model=list[PipelineRunSummaryResponse])
def list_runs(
    db: DbSession,
    lead_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    """List recent pipeline runs to inspect active and failed flows."""
    return list_pipeline_runs(db, lead_id=lead_id, status=status, limit=limit)


@router.get("/runs/{pipeline_run_id}/context")
def get_run_context(pipeline_run_id: uuid.UUID, db: DbSession):
    """Return accumulated step_context_json for a pipeline run.

    Shows what each pipeline step found: enrichment signals, scoring,
    analysis reasoning, research findings, brief assessment, reviewer notes.
    """
    from app.services.pipeline.context_service import get_step_context

    context = get_step_context(db, pipeline_run_id)
    if not context:
        raise HTTPException(status_code=404, detail="Pipeline run not found or has no context")
    return context


@router.get("/runs/{pipeline_run_id}", response_model=PipelineRunDetailResponse)
def get_run(pipeline_run_id: uuid.UUID, db: DbSession):
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


@router.post("/runs/{pipeline_run_id}/resume")
def resume_pipeline_run(pipeline_run_id: uuid.UUID, db: DbSession):
    """Resume a stuck pipeline run by re-dispatching the next step."""
    from app.models.task_tracking import PipelineRun

    run = db.get(PipelineRun, pipeline_run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run.finished_at is not None:
        raise HTTPException(status_code=400, detail=f"Pipeline already finished with status: {run.status}")
    if run.status not in {"running", "failed"}:
        raise HTTPException(status_code=400, detail=f"Cannot resume pipeline in status: {run.status}")

    lead_id = str(run.lead_id)
    run_id = str(run.id)
    correlation_id = run.correlation_id

    # Determine the next step based on current_step
    step = run.current_step or "pipeline_dispatch"
    step_chain = {
        "pipeline_dispatch": "task_enrich_lead",
        "enrichment": "task_score_lead",
        "scoring": "task_analyze_lead",
        "analysis": "task_analyze_lead",  # re-trigger analysis to decide branch
        "research": "task_generate_brief",
        "scout": "task_generate_brief",  # Scout stuck → skip to brief
        "brief_generation": "task_review_brief",
        "brief_review": "task_generate_draft",
        "draft_generation": None,  # terminal
    }

    next_task_name = step_chain.get(step)
    if next_task_name is None:
        raise HTTPException(status_code=400, detail=f"No next step after: {step}")

    # Dispatch the next task
    from app.workers import tasks as task_module
    task_fn = getattr(task_module, next_task_name, None)
    if task_fn is None:
        raise HTTPException(status_code=500, detail=f"Task function not found: {next_task_name}")

    run.status = "running"
    db.commit()

    task_fn.delay(lead_id, pipeline_run_id=run_id, correlation_id=correlation_id)

    return {
        "ok": True,
        "pipeline_run_id": str(run.id),
        "resumed_from": step,
        "next_task": next_task_name,
    }


@router.post("/batch")
def start_batch_pipeline(request: Request, db: DbSession):
    """Start the batch pipeline that processes all 'new' leads."""
    existing = get_batch_pipeline_task_run(db)
    if existing and existing.status in {"queued", "running", "retrying", "stopping"}:
        return {
            "ok": False,
            "message": "El pipeline batch ya esta corriendo.",
            "progress": get_batch_pipeline_status_snapshot(db),
        }

    legacy = load_batch_pipeline_legacy_status()
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
def get_batch_pipeline_status(db: DbSession):
    """Poll batch pipeline progress."""
    return get_batch_pipeline_status_snapshot(db)


@router.post("/batch/stop")
def stop_batch_pipeline(db: DbSession):
    """Signal the batch pipeline to stop after the current lead."""
    task_run = request_task_stop(
        db,
        task_name="task_batch_pipeline",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
    )
    if task_run:
        return {"ok": True, "message": "Pipeline batch deteniéndose tras el lead actual."}

    if mark_batch_pipeline_legacy_stop_requested():
        return {"ok": True, "message": "Pipeline batch deteniéndose tras el lead actual."}
    return {"ok": True, "message": "No habia pipeline corriendo."}
