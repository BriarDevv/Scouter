"""Outcome analysis service — correlates pipeline decisions with WON/LOST results.

Queries OutcomeSnapshot data to identify:
- Which signals predict WON vs LOST
- Which quality ratings were accurate
- Which industries/cities convert best
- Scoring weight recommendations based on empirical data
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.outcome_snapshot import OutcomeSnapshot
from app.models.review_correction import ReviewCorrection

logger = get_logger(__name__)


def get_outcome_summary(db: Session) -> dict:
    """High-level outcome summary for dashboard and reports."""
    snapshots = db.query(OutcomeSnapshot).all()
    if not snapshots:
        return {"total": 0, "won": 0, "lost": 0, "win_rate": 0, "sufficient_data": False}

    won = [s for s in snapshots if s.outcome == "won"]
    lost = [s for s in snapshots if s.outcome == "lost"]
    total = len(snapshots)

    return {
        "total": total,
        "won": len(won),
        "lost": len(lost),
        "win_rate": round(len(won) / total, 2) if total > 0 else 0,
        "sufficient_data": total >= 50,
    }


def analyze_signal_correlations(db: Session) -> list[dict]:
    """Which signals correlate with WON vs LOST outcomes.

    Returns a list sorted by win_rate descending.
    """
    snapshots = db.query(OutcomeSnapshot).all()
    if not snapshots:
        return []

    signal_stats: dict[str, dict] = {}
    for s in snapshots:
        for sig in s.signals_json or []:
            if sig not in signal_stats:
                signal_stats[sig] = {"signal": sig, "won": 0, "lost": 0, "total": 0}
            signal_stats[sig][s.outcome] += 1
            signal_stats[sig]["total"] += 1

    result = []
    for stats in signal_stats.values():
        total = stats["total"]
        stats["win_rate"] = round(stats["won"] / total, 2) if total > 0 else 0
        result.append(stats)

    return sorted(result, key=lambda x: (-x["win_rate"], -x["total"]))


def analyze_quality_accuracy(db: Session) -> list[dict]:
    """How accurate were quality ratings — did HIGH leads actually convert?"""
    snapshots = db.query(OutcomeSnapshot).all()
    if not snapshots:
        return []

    quality_stats: dict[str, dict] = {}
    for s in snapshots:
        q = s.lead_quality or "unknown"
        if q not in quality_stats:
            quality_stats[q] = {"quality": q, "won": 0, "lost": 0, "total": 0}
        quality_stats[q][s.outcome] += 1
        quality_stats[q]["total"] += 1

    result = []
    for stats in quality_stats.values():
        total = stats["total"]
        stats["win_rate"] = round(stats["won"] / total, 2) if total > 0 else 0
        result.append(stats)

    return sorted(result, key=lambda x: -x["win_rate"])


def analyze_industry_performance(db: Session) -> list[dict]:
    """Which industries convert best?"""
    snapshots = db.query(OutcomeSnapshot).all()
    if not snapshots:
        return []

    industry_stats: dict[str, dict] = {}
    for s in snapshots:
        ind = s.industry or "unknown"
        if ind not in industry_stats:
            industry_stats[ind] = {"industry": ind, "won": 0, "lost": 0, "total": 0}
        industry_stats[ind][s.outcome] += 1
        industry_stats[ind]["total"] += 1

    result = []
    for stats in industry_stats.values():
        total = stats["total"]
        stats["win_rate"] = round(stats["won"] / total, 2) if total > 0 else 0
        result.append(stats)

    return sorted(result, key=lambda x: (-x["win_rate"], -x["total"]))


def generate_scoring_recommendations(db: Session) -> list[dict]:
    """Generate scoring weight recommendations based on outcome data.

    Compares signal win rates to identify which signals deserve more/less weight.
    Only generates recommendations when there's sufficient data (≥50 outcomes).
    """
    summary = get_outcome_summary(db)
    if not summary["sufficient_data"]:
        return [
            {
                "type": "info",
                "description": f"Datos insuficientes: {summary['total']} outcomes (necesitamos ≥50)",
                "evidence": f"{summary['won']} WON, {summary['lost']} LOST",
                "action": "Seguir acumulando outcomes",
            }
        ]

    signal_data = analyze_signal_correlations(db)
    avg_win_rate = summary["win_rate"]
    recommendations = []

    for sig in signal_data:
        if sig["total"] < 5:
            continue  # Not enough data for this signal

        diff = sig["win_rate"] - avg_win_rate
        if diff > 0.15:
            recommendations.append(
                {
                    "type": "increase_weight",
                    "signal": sig["signal"],
                    "description": f"{sig['signal']} tiene win rate {sig['win_rate']:.0%} vs promedio {avg_win_rate:.0%}",
                    "evidence": f"{sig['won']} WON / {sig['total']} total",
                    "action": f"Aumentar peso de {sig['signal']} en scoring (+5 a +10 puntos)",
                }
            )
        elif diff < -0.15:
            recommendations.append(
                {
                    "type": "decrease_weight",
                    "signal": sig["signal"],
                    "description": f"{sig['signal']} tiene win rate {sig['win_rate']:.0%} vs promedio {avg_win_rate:.0%}",
                    "evidence": f"{sig['won']} WON / {sig['total']} total",
                    "action": f"Reducir peso de {sig['signal']} en scoring (-5 puntos)",
                }
            )

    # Industry recommendations
    industry_data = analyze_industry_performance(db)
    for ind in industry_data:
        if ind["total"] < 5:
            continue
        if ind["win_rate"] > avg_win_rate + 0.2:
            recommendations.append(
                {
                    "type": "high_value_industry",
                    "signal": ind["industry"],
                    "description": f'Industria "{ind["industry"]}" convierte a {ind["win_rate"]:.0%}',
                    "evidence": f"{ind['won']} WON / {ind['total']} total",
                    "action": f'Agregar "{ind["industry"]}" a HIGH_VALUE_INDUSTRIES si no está',
                }
            )

    # Correction pattern recommendations
    corrections = (
        db.query(ReviewCorrection.category, ReviewCorrection.issue)
        .order_by(ReviewCorrection.created_at.desc())
        .limit(100)
        .all()
    )
    if corrections:
        category_counts = Counter(
            c[0].value if hasattr(c[0], "value") else c[0] for c in corrections
        )
        for cat, count in category_counts.most_common(3):
            if count >= 5:
                recommendations.append(
                    {
                        "type": "prompt_improvement",
                        "signal": cat,
                        "description": f'Reviewer corrigio "{cat}" {count} veces en las ultimas 100 reviews',
                        "evidence": f"{count} correcciones",
                        "action": f"Mejorar prompt del Executor para reducir errores de {cat}",
                    }
                )

    logger.info(
        "scoring_recommendations_generated",
        total_outcomes=summary["total"],
        recommendations_count=len(recommendations),
    )
    return recommendations
