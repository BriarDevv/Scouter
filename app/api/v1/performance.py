import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import (
    CityBreakdownResponse,
    IndustryBreakdownResponse,
    SourcePerformanceResponse,
)
from app.schemas.performance import (
    AIHealthResponse,
    AnalysisSummaryResponse,
    InvestigationDetailResponse,
    OutcomeAnalyticsResponse,
    ScoringRecommendationItem,
    SignalCorrelationItem,
)
from app.services.dashboard.dashboard_service import (
    get_ai_health_summary,
    get_city_breakdown,
    get_industry_breakdown,
    get_investigation_detail,
    get_source_performance,
)

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/industry", response_model=list[IndustryBreakdownResponse])
def industry(db: Session = Depends(get_db)):
    """Return a simple industry breakdown using current lead and status data."""
    return get_industry_breakdown(db)


@router.get("/city", response_model=list[CityBreakdownResponse])
def city(db: Session = Depends(get_db)):
    """Return a simple city breakdown using current lead and status data."""
    return get_city_breakdown(db)


@router.get("/source", response_model=list[SourcePerformanceResponse])
def source(db: Session = Depends(get_db)):
    """Return a simple source performance breakdown using current lead and status data."""
    return get_source_performance(db)


@router.get("/ai-health", response_model=AIHealthResponse)
def get_ai_health(db: Session = Depends(get_db)):
    """AI health metrics: approval rate, fallback rate, avg latency, invocation count (24h)."""
    return get_ai_health_summary(db)


@router.get("/outcomes", response_model=OutcomeAnalyticsResponse)
def get_outcome_analytics(db: Session = Depends(get_db)):
    """Outcome analytics: WON/LOST breakdown by quality, industry, signals. Delegates to analysis
    service."""
    from app.services.pipeline.outcome_analysis_service import (
        analyze_industry_performance,
        analyze_quality_accuracy,
        analyze_signal_correlations,
        get_outcome_summary,
    )

    summary = get_outcome_summary(db)
    signals = analyze_signal_correlations(db)
    return {
        "total_won": summary["won"],
        "total_lost": summary["lost"],
        "by_industry": analyze_industry_performance(db),
        "by_quality": analyze_quality_accuracy(db),
        "top_signals_won": [{"signal": s["signal"], "count": s["won"]} for s in signals[:10]],
    }


@router.get("/outcomes/signals", response_model=list[SignalCorrelationItem])
def get_signal_correlation(db: Session = Depends(get_db)):
    """Which signals correlate with WON vs LOST outcomes. Delegates to analysis service."""
    from app.services.pipeline.outcome_analysis_service import analyze_signal_correlations

    return analyze_signal_correlations(db)


@router.get("/recommendations", response_model=list[ScoringRecommendationItem])
def get_scoring_recommendations(db: Session = Depends(get_db)):
    """Scoring and prompt improvement recommendations from outcome data."""
    from app.services.pipeline.outcome_analysis_service import generate_scoring_recommendations

    return generate_scoring_recommendations(db)


@router.get("/analysis/summary", response_model=AnalysisSummaryResponse)
def get_analysis_summary(db: Session = Depends(get_db)):
    """Full outcome analysis: summary, signals, quality accuracy, industry performance."""
    from app.services.pipeline.outcome_analysis_service import (
        analyze_industry_performance,
        analyze_quality_accuracy,
        analyze_signal_correlations,
        get_outcome_summary,
    )

    return {
        "summary": get_outcome_summary(db),
        "signal_correlations": analyze_signal_correlations(db),
        "quality_accuracy": analyze_quality_accuracy(db),
        "industry_performance": analyze_industry_performance(db),
    }


@router.get("/investigations/{lead_id}", response_model=InvestigationDetailResponse)
def get_investigation(lead_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return Scout investigation thread for a lead."""
    result = get_investigation_detail(db, lead_id)
    if not result:
        raise HTTPException(status_code=404, detail="No investigation found for this lead")
    return result
