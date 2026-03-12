import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models.lead import LeadStatus
from app.schemas.lead import (
    LeadCreate,
    LeadDetailResponse,
    LeadListResponse,
    LeadResponse,
    LeadSignalResponse,
)
from app.services.lead_service import create_lead, get_lead, list_leads

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=201)
def create(data: LeadCreate, db: Session = Depends(get_session)):
    """Create a new lead. Deduplicates automatically."""
    try:
        lead = create_lead(db, data)
        return lead
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=LeadListResponse)
def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: LeadStatus | None = None,
    min_score: float | None = None,
    db: Session = Depends(get_session),
):
    """List leads with pagination and optional filters."""
    leads, total = list_leads(db, page=page, page_size=page_size, status=status, min_score=min_score)
    return LeadListResponse(items=leads, total=total, page=page, page_size=page_size)


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_by_id(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Get a lead by ID with all signals."""
    lead = get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadDetailResponse(
        **LeadResponse.model_validate(lead).model_dump(),
        signals=[LeadSignalResponse.model_validate(s) for s in lead.signals],
    )
