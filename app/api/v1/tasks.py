from datetime import UTC, datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.task_tracking import TaskStatusResponse
from app.services.task_tracking_service import get_pipeline_run, get_task_run, list_task_runs
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _merge_task_view(db: Session, task_run) -> TaskStatusResponse:
    pipeline_run = None
    if task_run.pipeline_run_id:
        pipeline_run = get_pipeline_run(db, task_run.pipeline_run_id)

    status = task_run.status
    current_step = task_run.current_step
    result = task_run.result
    error = task_run.error
    updated_at = task_run.updated_at
    started_at = task_run.started_at
    finished_at = task_run.finished_at

    if pipeline_run and task_run.task_name == "task_full_pipeline":
        status = pipeline_run.status
        current_step = pipeline_run.current_step
        result = pipeline_run.result or result
        error = pipeline_run.error or error
        updated_at = pipeline_run.updated_at
        started_at = pipeline_run.started_at or started_at
        finished_at = pipeline_run.finished_at or finished_at

    return TaskStatusResponse(
        task_id=task_run.task_id,
        status=status,
        queue=task_run.queue,
        lead_id=task_run.lead_id,
        pipeline_run_id=task_run.pipeline_run_id,
        current_step=current_step,
        correlation_id=task_run.correlation_id,
        result=result,
        error=error,
        created_at=task_run.created_at,
        updated_at=updated_at,
        started_at=started_at,
        finished_at=finished_at,
    )


@router.get("", response_model=list[TaskStatusResponse])
def list_tasks(
    status: str | None = None,
    lead_id: uuid.UUID | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """List recent tracked tasks for operator workflows and future supervisors."""
    return [
        _merge_task_view(db, task_run)
        for task_run in list_task_runs(
            db,
            status=status,
            lead_id=lead_id,
            pipeline_run_id=pipeline_run_id,
            limit=limit,
        )
    ]


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(task_id: str, db: Session = Depends(get_session)):
    """Return the persisted status of an async task."""
    task_run = get_task_run(db, task_id)
    if task_run:
        return _merge_task_view(db, task_run)

    try:
        async_result = celery_app.AsyncResult(task_id)
        state = async_result.state
        if state != "PENDING":
            result = async_result.result if isinstance(async_result.result, dict) else None
            error = None if state == "SUCCESS" else str(async_result.result)
            now = datetime.now(UTC)
            return TaskStatusResponse(
                task_id=task_id,
                status=state.lower(),
                result=result,
                error=error,
                created_at=now,
                updated_at=now,
            )
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/revoke")
def revoke_task(task_id: str):
    """Revoke/terminate a running Celery task."""
    try:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        return {"ok": True, "task_id": task_id, "message": "Task revocada."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
