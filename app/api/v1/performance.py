import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models.investigation_thread import InvestigationThread
from app.schemas.dashboard import (
    CityBreakdownResponse,
    IndustryBreakdownResponse,
    SourcePerformanceResponse,
)
from app.services.dashboard_svc.dashboard_service import (
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


@router.get("/ai-health")
def get_ai_health(db: Session = Depends(get_session)):
    """AI health metrics: approval rate, fallback rate, avg latency, invocation count (24h)."""
    from datetime import UTC, datetime, timedelta
    from app.models.llm_invocation import LLMInvocation

    since = datetime.now(UTC) - timedelta(hours=24)

    total = db.query(func.count(LLMInvocation.id)).filter(LLMInvocation.created_at >= since).scalar() or 0
    succeeded = db.query(func.count(LLMInvocation.id)).filter(
        LLMInvocation.created_at >= since, LLMInvocation.status == "succeeded"
    ).scalar() or 0
    fallbacks = db.query(func.count(LLMInvocation.id)).filter(
        LLMInvocation.created_at >= since, LLMInvocation.fallback_used.is_(True)
    ).scalar() or 0
    avg_latency = db.query(func.avg(LLMInvocation.latency_ms)).filter(
        LLMInvocation.created_at >= since, LLMInvocation.latency_ms.isnot(None)
    ).scalar()

    return {
        "approval_rate": round(succeeded / max(total, 1), 2),
        "fallback_rate": round(fallbacks / max(total, 1), 2),
        "avg_latency_ms": round(avg_latency) if avg_latency else None,
        "invocations_24h": total,
    }


@router.get("/outcomes")
def get_outcome_analytics(db: Session = Depends(get_session)):
    """Outcome analytics: WON/LOST breakdown by quality, industry, signals. Delegates to analysis service."""
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


@router.get("/outcomes/signals")
def get_signal_correlation(db: Session = Depends(get_session)):
    """Which signals correlate with WON vs LOST outcomes. Delegates to analysis service."""
    from app.services.pipeline.outcome_analysis_service import analyze_signal_correlations
    return analyze_signal_correlations(db)


@router.get("/recommendations")
def get_scoring_recommendations(db: Session = Depends(get_session)):
    """Scoring and prompt improvement recommendations from outcome data."""
    from app.services.pipeline.outcome_analysis_service import generate_scoring_recommendations
    return generate_scoring_recommendations(db)


@router.get("/analysis/summary")
def get_analysis_summary(db: Session = Depends(get_session)):
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


@router.get("/investigations/{lead_id}")
def get_investigation(lead_id: uuid.UUID, db: Session = Depends(get_session)):
    """Return Scout investigation thread for a lead."""
    thread = (
        db.query(InvestigationThread)
        .filter_by(lead_id=lead_id)
        .order_by(InvestigationThread.created_at.desc())
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="No investigation found for this lead")

    return {
        "id": str(thread.id),
        "lead_id": str(thread.lead_id),
        "agent_model": thread.agent_model,
        "tool_calls": thread.tool_calls_json,
        "pages_visited": thread.pages_visited_json,
        "findings": thread.findings_json,
        "loops_used": thread.loops_used,
        "duration_ms": thread.duration_ms,
        "error": thread.error,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
    }
