import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.request_context import get_correlation_id
from app.schemas.lead import LeadResponse
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.scoring_service import score_lead
from app.services.task_tracking_service import (
    attach_pipeline_root_task,
    create_pipeline_run,
    queue_task_run,
)
from app.workers.tasks import task_analyze_lead, task_full_pipeline

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/rescore-all")
def rescore_all_leads():
    """Re-score all leads. Useful after scoring weight changes."""
    from app.workers.tasks import task_rescore_all
    task = task_rescore_all.delay()
    return {"task_id": str(task.id), "status": "queued"}


@router.post("/{lead_id}", response_model=LeadResponse)
def score(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Score a lead synchronously based on its signals."""
    lead = score_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/analyze", response_model=TaskEnqueueResponse)
def analyze_with_llm(
    lead_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_session),
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
    db: Session = Depends(get_session),
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
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "default",
        "lead_id": lead_id,
        "pipeline_run_id": pipeline_run.id,
        "current_step": "pipeline_dispatch",
    }
