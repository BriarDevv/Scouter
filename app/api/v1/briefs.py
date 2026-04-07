"""Commercial brief endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.commercial_brief import CommercialBrief
from app.schemas.brief import CommercialBriefResponse

router = APIRouter(prefix="/briefs", tags=["briefs"])


@router.get("/leads/{lead_id}", response_model=CommercialBriefResponse)
def get_brief_for_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get the commercial brief for a specific lead."""
    brief = db.query(CommercialBrief).filter_by(lead_id=lead_id).first()
    if not brief:
        raise HTTPException(404, "No commercial brief found for this lead")
    return brief


@router.post("/leads/{lead_id}", response_model=CommercialBriefResponse)
def generate_brief_for_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Generate a commercial brief for a lead."""
    from app.services.research.brief_service import generate_brief

    brief = generate_brief(db, lead_id)
    if not brief:
        raise HTTPException(404, "Lead not found")
    return brief


@router.get("", response_model=list[CommercialBriefResponse])
def list_briefs(
    budget_tier: str | None = None,
    contact_priority: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List commercial briefs with optional filters."""
    query = db.query(CommercialBrief)
    if budget_tier:
        query = query.filter(CommercialBrief.budget_tier == budget_tier)
    if contact_priority:
        query = query.filter(CommercialBrief.contact_priority == contact_priority)
    return query.order_by(CommercialBrief.created_at.desc()).limit(limit).all()
