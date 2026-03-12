import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.lead import LeadResponse
from app.services.scoring_service import score_lead
from app.workers.tasks import task_analyze_lead, task_full_pipeline, task_score_lead

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/{lead_id}", response_model=LeadResponse)
def score(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Score a lead synchronously based on its signals."""
    lead = score_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/analyze")
def analyze_with_llm(lead_id: uuid.UUID):
    """Queue LLM analysis (summary + quality evaluation) as an async task."""
    task = task_analyze_lead.delay(str(lead_id))
    return {"task_id": task.id, "status": "queued"}


@router.post("/{lead_id}/pipeline")
def run_full_pipeline(lead_id: uuid.UUID):
    """Run the full pipeline: enrich -> score -> LLM analyze -> generate draft."""
    task = task_full_pipeline.delay(str(lead_id))
    return {"task_id": task.id, "status": "pipeline_queued"}
