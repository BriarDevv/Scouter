import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
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
