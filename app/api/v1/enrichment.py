import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.lead import LeadResponse
from app.schemas.task_tracking import TaskEnqueueResponse
from app.services.enrichment_service import enrich_lead
from app.services.task_tracking_service import queue_task_run
from app.workers.tasks import task_enrich_lead

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/{lead_id}", response_model=LeadResponse)
def enrich(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Run enrichment on a lead synchronously."""
    lead = enrich_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/async", response_model=TaskEnqueueResponse)
def enrich_async(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Queue enrichment as an async Celery task."""
    task = task_enrich_lead.delay(str(lead_id))
    queue_task_run(
        db,
        task_id=task.id,
        task_name="task_enrich_lead",
        queue="enrichment",
        lead_id=lead_id,
        current_step="enrichment",
    )
    return {
        "task_id": task.id,
        "status": "queued",
        "queue": "enrichment",
        "lead_id": lead_id,
        "current_step": "enrichment",
    }
