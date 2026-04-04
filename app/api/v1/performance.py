import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models.investigation_thread import InvestigationThread
from app.models.outcome_snapshot import OutcomeSnapshot
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


@router.get("/outcomes")
def get_outcome_analytics(db: Session = Depends(get_session)):
    """Outcome analytics: WON/LOST breakdown by quality, industry, signals.

    Enables Phase 4 learning — correlates pipeline decisions with results.
    """
    snapshots = db.query(OutcomeSnapshot).all()
    if not snapshots:
        return {"total_won": 0, "total_lost": 0, "by_industry": [], "by_quality": [], "top_signals_won": []}

    won = [s for s in snapshots if s.outcome == "won"]
    lost = [s for s in snapshots if s.outcome == "lost"]

    # By industry
    industry_stats: dict[str, dict] = {}
    for s in snapshots:
        ind = s.industry or "unknown"
        if ind not in industry_stats:
            industry_stats[ind] = {"industry": ind, "won": 0, "lost": 0}
        industry_stats[ind][s.outcome] += 1

    # By quality
    quality_stats: dict[str, dict] = {}
    for s in snapshots:
        q = s.lead_quality or "unknown"
        if q not in quality_stats:
            quality_stats[q] = {"quality": q, "won": 0, "lost": 0}
        quality_stats[q][s.outcome] += 1

    # Top signals for won leads
    signal_counts: dict[str, int] = {}
    for s in won:
        for sig in (s.signals_json or []):
            signal_counts[sig] = signal_counts.get(sig, 0) + 1
    top_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_won": len(won),
        "total_lost": len(lost),
        "by_industry": sorted(industry_stats.values(), key=lambda x: x["won"], reverse=True),
        "by_quality": sorted(quality_stats.values(), key=lambda x: x["won"], reverse=True),
        "top_signals_won": [{"signal": s, "count": c} for s, c in top_signals],
    }


@router.get("/outcomes/signals")
def get_signal_correlation(db: Session = Depends(get_session)):
    """Which signals correlate with WON vs LOST outcomes."""
    snapshots = db.query(OutcomeSnapshot).all()
    if not snapshots:
        return []

    signal_stats: dict[str, dict] = {}
    for s in snapshots:
        for sig in (s.signals_json or []):
            if sig not in signal_stats:
                signal_stats[sig] = {"signal": sig, "won": 0, "lost": 0, "total": 0}
            signal_stats[sig][s.outcome] += 1
            signal_stats[sig]["total"] += 1

    result = []
    for stats in signal_stats.values():
        total = stats["total"]
        stats["win_rate"] = round(stats["won"] / total, 2) if total > 0 else 0
        result.append(stats)

    return sorted(result, key=lambda x: x["win_rate"], reverse=True)


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
