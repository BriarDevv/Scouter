import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.request_context import get_correlation_id
from app.schemas.lead import LeadResponse
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.leads.enrichment_service import enrich_lead
from app.services.pipeline.task_tracking_service import queue_task_run
from app.workers.tasks import task_enrich_lead

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/{lead_id}", response_model=LeadResponse)
def enrich(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Run enrichment on a lead synchronously."""
    lead = enrich_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/async", response_model=TaskEnqueueResponse)
def enrich_async(
    lead_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Queue enrichment as an async Celery task."""
    correlation_id = get_correlation_id(request)
    task = task_enrich_lead.delay(str(lead_id), correlation_id=correlation_id)
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_enrich_lead",
        queue="enrichment",
        lead_id=lead_id,
        correlation_id=correlation_id,
        current_step="enrichment",
    )
    db.commit()
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "enrichment",
        "lead_id": lead_id,
        "current_step": "enrichment",
    }
