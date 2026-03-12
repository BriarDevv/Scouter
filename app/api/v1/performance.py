from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.dashboard import (
    CityBreakdownResponse,
    IndustryBreakdownResponse,
    SourcePerformanceResponse,
)
from app.services.dashboard_service import (
    get_city_breakdown,
    get_industry_breakdown,
    get_source_performance,
)

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/industry", response_model=list[IndustryBreakdownResponse])
def industry(db: Session = Depends(get_session)):
    """Return a simple industry breakdown using current lead and status data."""
    return get_industry_breakdown(db)


@router.get("/city", response_model=list[CityBreakdownResponse])
def city(db: Session = Depends(get_session)):
    """Return a simple city breakdown using current lead and status data."""
    return get_city_breakdown(db)


@router.get("/source", response_model=list[SourcePerformanceResponse])
def source(db: Session = Depends(get_session)):
    """Return a simple source performance breakdown using current lead and status data."""
    return get_source_performance(db)
