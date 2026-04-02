"""Tests for idempotency guards in pipeline tasks."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from app.models.lead import Lead, LeadStatus


def test_enrich_skips_already_enriched(db):
    """task_enrich_lead should skip if lead.enriched_at is set."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Test Biz",
        city="Buenos Aires",
        status=LeadStatus.ENRICHED,
        enriched_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    db.commit()

    with patch("app.workers.tasks.enrich_lead") as mock_enrich:
        from app.workers.tasks import task_enrich_lead
        result = task_enrich_lead(str(lead.id))
        assert result["status"] == "skipped"
        assert result["reason"] == "already_enriched"
        mock_enrich.assert_not_called()


def test_score_skips_already_scored(db):
    """task_score_lead should skip if lead.scored_at is set."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Test Biz",
        city="Buenos Aires",
        status=LeadStatus.SCORED,
        score=75.0,
        scored_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    db.commit()

    with patch("app.workers.tasks.score_lead") as mock_score:
        from app.workers.tasks import task_score_lead
        result = task_score_lead(str(lead.id))
        assert result["status"] == "skipped"
        assert result["reason"] == "already_scored"
        mock_score.assert_not_called()


def test_analyze_skips_already_analyzed(db):
    """task_analyze_lead should skip if lead.llm_summary is set."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Test Biz",
        city="Buenos Aires",
        status=LeadStatus.SCORED,
        score=75.0,
        llm_summary="Already analyzed",
        llm_quality="high",
    )
    db.add(lead)
    db.commit()

    with patch("app.workers.tasks.summarize_business") as mock_llm:
        from app.workers.tasks import task_analyze_lead
        result = task_analyze_lead(str(lead.id))
        assert result["status"] == "skipped"
        assert result["reason"] == "already_analyzed"
        mock_llm.assert_not_called()
