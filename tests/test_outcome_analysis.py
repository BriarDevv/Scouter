"""Tests for outcome analysis service — signal correlations, quality accuracy, recommendations."""

from app.models.lead import Lead
from app.models.outcome_snapshot import OutcomeSnapshot
from app.models.review_correction import CorrectionCategory, CorrectionSeverity, ReviewCorrection
from app.services.pipeline.outcome_analysis_service import (
    analyze_industry_performance,
    analyze_quality_accuracy,
    analyze_signal_correlations,
    generate_scoring_recommendations,
    get_outcome_summary,
)


def _make_lead(db) -> Lead:
    lead = Lead(business_name="Outcome Test", city="CABA", industry="Test")
    db.add(lead)
    db.flush()
    return lead


def _seed_snapshot(db, outcome="won", signals=None, quality="high", industry="Gastronomia"):
    lead = _make_lead(db)
    snap = OutcomeSnapshot(
        lead_id=lead.id,
        outcome=outcome,
        lead_score=80,
        lead_quality=quality,
        industry=industry,
        signals_json=signals or [],
    )
    db.add(snap)
    db.commit()
    return snap


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def test_summary_empty(db):
    result = get_outcome_summary(db)
    assert result["total"] == 0
    assert result["sufficient_data"] is False


def test_summary_with_data(db):
    _seed_snapshot(db, "won")
    _seed_snapshot(db, "won")
    _seed_snapshot(db, "lost")

    result = get_outcome_summary(db)
    assert result["total"] == 3
    assert result["won"] == 2
    assert result["lost"] == 1
    assert result["win_rate"] == 0.67
    assert result["sufficient_data"] is False  # < 50


# ---------------------------------------------------------------------------
# Signal correlations
# ---------------------------------------------------------------------------


def test_signal_correlations_empty(db):
    assert analyze_signal_correlations(db) == []


def test_signal_correlations_with_data(db):
    _seed_snapshot(db, "won", signals=["no_website", "weak_seo"])
    _seed_snapshot(db, "won", signals=["no_website"])
    _seed_snapshot(db, "lost", signals=["no_website", "has_website"])

    result = analyze_signal_correlations(db)
    signals_by_name = {s["signal"]: s for s in result}

    assert "no_website" in signals_by_name
    nw = signals_by_name["no_website"]
    assert nw["won"] == 2
    assert nw["lost"] == 1
    assert nw["total"] == 3
    assert nw["win_rate"] == 0.67


# ---------------------------------------------------------------------------
# Quality accuracy
# ---------------------------------------------------------------------------


def test_quality_accuracy_empty(db):
    assert analyze_quality_accuracy(db) == []


def test_quality_accuracy_with_data(db):
    _seed_snapshot(db, "won", quality="high")
    _seed_snapshot(db, "won", quality="high")
    _seed_snapshot(db, "lost", quality="high")
    _seed_snapshot(db, "lost", quality="low")

    result = analyze_quality_accuracy(db)
    by_quality = {q["quality"]: q for q in result}
    assert by_quality["high"]["win_rate"] == 0.67
    assert by_quality["low"]["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# Industry performance
# ---------------------------------------------------------------------------


def test_industry_empty(db):
    assert analyze_industry_performance(db) == []


def test_industry_with_data(db):
    _seed_snapshot(db, "won", industry="Tech")
    _seed_snapshot(db, "won", industry="Tech")
    _seed_snapshot(db, "lost", industry="Retail")

    result = analyze_industry_performance(db)
    by_ind = {i["industry"]: i for i in result}
    assert by_ind["Tech"]["win_rate"] == 1.0
    assert by_ind["Retail"]["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# Scoring recommendations
# ---------------------------------------------------------------------------


def test_recommendations_insufficient_data(db):
    _seed_snapshot(db, "won")
    result = generate_scoring_recommendations(db)
    assert len(result) == 1
    assert result[0]["type"] == "info"
    assert "insuficientes" in result[0]["description"].lower()


def test_recommendations_with_corrections(db):
    # Seed 50+ outcomes for sufficient data
    for _ in range(30):
        _seed_snapshot(db, "won")
    for _ in range(25):
        _seed_snapshot(db, "lost")

    # Seed corrections with a repeated pattern
    for _ in range(8):
        corr_lead = _make_lead(db)
        db.add(
            ReviewCorrection(
                lead_id=corr_lead.id,
                review_type="draft_review",
                category=CorrectionCategory.TONE,
                severity=CorrectionSeverity.IMPORTANT,
                issue="Tono demasiado formal",
            )
        )
    db.commit()

    result = generate_scoring_recommendations(db)
    types = [r["type"] for r in result]
    assert "prompt_improvement" in types
    tone_rec = next(r for r in result if r["signal"] == "tone")
    assert "8" in tone_rec["evidence"]
