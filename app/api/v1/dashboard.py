from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import (
    DashboardStatsResponse,
    GeoSummaryCityResponse,
    PipelineStageResponse,
    TimeSeriesPointResponse,
)
from app.schemas.outreach import OutreachLogResponse
from app.services.dashboard.dashboard_service import (
    get_city_breakdown,
    get_dashboard_stats,
    get_pipeline_breakdown,
    get_recent_activity,
    get_time_series,
)
from app.data.cities_ar import get_coords

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def stats(db: Session = Depends(get_db)):
    """Return top-level dashboard metrics inferred from current leads and outreach state."""
    return get_dashboard_stats(db)


@router.get("/pipeline", response_model=list[PipelineStageResponse])
def pipeline(db: Session = Depends(get_db)):
    """Return a cumulative funnel view based on the current lead status snapshot."""
    return get_pipeline_breakdown(db)


@router.get("/time-series", response_model=list[TimeSeriesPointResponse])
def time_series(days: int = Query(30, ge=1, le=90), db: Session = Depends(get_db)):
    """Return day-by-day counts for leads, sent outreach, replies, and wins."""
    return get_time_series(db, days=days)


@router.get("/activity", response_model=list[OutreachLogResponse])
def activity(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)):
    """Return recent outreach activity for the overview feed."""
    return get_recent_activity(db, limit=limit)


@router.get("/geo-summary", response_model=list[GeoSummaryCityResponse])
def geo_summary(db: Session = Depends(get_db)):
    """Return city aggregation with coordinates for the map view."""
    city_data = get_city_breakdown(db)
    result: list[dict] = []
    for row in city_data:
        coords = get_coords(row["city"])
        if coords is None:
            continue
        lat, lng = coords
        # Count qualified leads (score >= 60) from city breakdown avg_score heuristic
        # We approximate qualified_count from count * ratio based on avg_score
        qualified_estimate = int(row["count"] * (min(row["avg_score"], 100) / 100))
        result.append(
            {
                "city": row["city"],
                "count": row["count"],
                "avg_score": row["avg_score"],
                "qualified_count": qualified_estimate,
                "lat": lat,
                "lng": lng,
            }
        )
    return result
