"""Tests for dashboard SQL aggregations and edge cases."""

from app.models.lead import Lead, LeadStatus


def test_dashboard_stats_with_no_leads(db):
    from app.services.dashboard_service import get_dashboard_stats
    stats = get_dashboard_stats(db)
    assert stats["total_leads"] == 0
    assert stats["avg_score"] == 0.0
    assert stats["conversion_rate"] == 0.0


def test_dashboard_stats_counts_correctly(db):
    from app.services.dashboard_service import get_dashboard_stats
    # Seed 3 leads with different statuses
    for i, status in enumerate([LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.WON]):
        lead = Lead(
            business_name=f"Test Lead {i}",
            status=status,
            score=50.0 + i * 10,
            dedup_hash=f"hash_{i}_{status.value}",
        )
        db.add(lead)
    db.commit()

    stats = get_dashboard_stats(db)
    assert stats["total_leads"] == 3
    assert stats["won"] == 1
    assert stats["contacted"] >= 1  # WON has reached contacted stage


def test_dashboard_pipeline_breakdown_returns_stages(db):
    from app.services.dashboard_service import get_pipeline_breakdown
    stages = get_pipeline_breakdown(db)
    assert isinstance(stages, list)
    assert len(stages) > 0
    assert all("stage" in s and "count" in s for s in stages)


def test_dashboard_time_series_returns_correct_days(db):
    from app.services.dashboard_service import get_time_series
    series = get_time_series(db, days=7)
    assert len(series) == 7
    assert all("date" in s and "leads" in s for s in series)


def test_dashboard_industry_breakdown_empty(db):
    from app.services.dashboard_service import get_industry_breakdown
    result = get_industry_breakdown(db)
    assert isinstance(result, list)


def test_dashboard_city_breakdown_empty(db):
    from app.services.dashboard_service import get_city_breakdown
    result = get_city_breakdown(db)
    assert isinstance(result, list)
