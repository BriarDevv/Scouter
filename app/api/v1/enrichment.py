import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.lead import LeadResponse
from app.services.enrichment_service import enrich_lead
from app.workers.tasks import task_enrich_lead

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/{lead_id}", response_model=LeadResponse)
def enrich(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Run enrichment on a lead synchronously."""
    lead = enrich_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/async")
def enrich_async(lead_id: uuid.UUID):
    """Queue enrichment as an async Celery task."""
    task = task_enrich_lead.delay(str(lead_id))
    return {"task_id": task.id, "status": "queued"}
