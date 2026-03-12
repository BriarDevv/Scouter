from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.dashboard import (
    DashboardStatsResponse,
    PipelineStageResponse,
    TimeSeriesPointResponse,
)
from app.schemas.outreach import OutreachLogResponse
from app.services.dashboard_service import (
    get_dashboard_stats,
    get_pipeline_breakdown,
    get_recent_activity,
    get_time_series,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def stats(db: Session = Depends(get_session)):
    """Return top-level dashboard metrics inferred from current leads and outreach state."""
    return get_dashboard_stats(db)


@router.get("/pipeline", response_model=list[PipelineStageResponse])
def pipeline(db: Session = Depends(get_session)):
    """Return a cumulative funnel view based on the current lead status snapshot."""
    return get_pipeline_breakdown(db)


@router.get("/time-series", response_model=list[TimeSeriesPointResponse])
def time_series(days: int = Query(30, ge=1, le=90), db: Session = Depends(get_session)):
    """Return day-by-day counts for leads, sent outreach, replies, and wins."""
    return get_time_series(db, days=days)


@router.get("/activity", response_model=list[OutreachLogResponse])
def activity(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_session)):
    """Return recent outreach activity for the overview feed."""
    return get_recent_activity(db, limit=limit)
