"""Commercial brief endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.brief import CommercialBriefResponse
from app.services.research.brief_service import (
    generate_brief,
)
from app.services.research.brief_service import (
    get_brief_for_lead as _get_brief_for_lead,
)
from app.services.research.brief_service import (
    list_briefs as _list_briefs,
)

router = APIRouter(prefix="/briefs", tags=["briefs"])


@router.get("/leads/{lead_id}", response_model=CommercialBriefResponse)
def get_brief_for_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get the commercial brief for a specific lead."""
    brief = _get_brief_for_lead(db, lead_id)
    if not brief:
        raise HTTPException(404, "No commercial brief found for this lead")
    return brief


@router.post("/leads/{lead_id}", response_model=CommercialBriefResponse)
def generate_brief_for_lead(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Generate a commercial brief for a lead."""
    brief = generate_brief(db, lead_id)
    if not brief:
        raise HTTPException(404, "Lead not found")
    return brief


@router.get("", response_model=list[CommercialBriefResponse])
def list_all_briefs(
    budget_tier: str | None = None,
    contact_priority: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List commercial briefs with optional filters."""
    return _list_briefs(db, budget_tier=budget_tier, contact_priority=contact_priority, limit=limit)
