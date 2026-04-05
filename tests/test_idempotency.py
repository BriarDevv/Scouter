"""Tests for idempotency guards in pipeline tasks."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from app.models.lead import Lead, LeadStatus
from app.models.task_tracking import PipelineRun


def _create_pipeline_run(db, lead_id, correlation_id):
    """Helper to create a PipelineRun so FK constraints pass."""
    run = PipelineRun(
        lead_id=lead_id,
        correlation_id=correlation_id,
        root_task_id=str(uuid.uuid4()),
        status="running",
        current_step="test",
    )
    db.add(run)
    db.commit()
    return str(run.id)


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

    with patch("app.workers.pipeline_tasks.enrich_lead") as mock_enrich:
        from app.workers.pipeline_tasks import task_enrich_lead
        result = task_enrich_lead(str(lead.id))
        assert result["status"] == "skipped"
        assert result["reason"] == "already_enriched"
        mock_enrich.assert_not_called()


def test_enrich_skip_chains_to_scoring(db):
    """task_enrich_lead must chain to task_score_lead even when skipping."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Chain Test Biz",
        city="Buenos Aires",
        status=LeadStatus.ENRICHED,
        enriched_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    db.commit()

    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with patch("app.workers.pipeline_tasks.task_score_lead.delay") as mock_delay:
        from app.workers.pipeline_tasks import task_enrich_lead
        result = task_enrich_lead(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "already_enriched"
        mock_delay.assert_called_once_with(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )


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

    with patch("app.workers.pipeline_tasks.score_lead") as mock_score:
        from app.workers.pipeline_tasks import task_score_lead
        result = task_score_lead(str(lead.id))
        assert result["status"] == "skipped"
        assert result["reason"] == "already_scored"
        mock_score.assert_not_called()


def test_score_skip_chains_to_analysis(db):
    """task_score_lead must chain to task_analyze_lead even when skipping."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Chain Score Biz",
        city="Buenos Aires",
        status=LeadStatus.SCORED,
        score=75.0,
        scored_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    db.commit()

    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with patch("app.workers.pipeline_tasks.task_analyze_lead.delay") as mock_delay:
        from app.workers.pipeline_tasks import task_score_lead
        result = task_score_lead(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )
        assert result["status"] == "skipped"
        assert result["reason"] == "already_scored"
        mock_delay.assert_called_once_with(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )


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

    with patch("app.workers.pipeline_tasks.run_lead_analysis_step") as mock_analysis:
        from app.workers.pipeline_tasks import task_analyze_lead
        result = task_analyze_lead(str(lead.id))
        assert result["status"] == "skipped"
        assert result["reason"] == "already_analyzed"
        mock_analysis.assert_not_called()


def test_analyze_skip_high_chains_to_research(db):
    """task_analyze_lead must chain to research when skipping a HIGH lead."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Chain Analyze HIGH",
        city="Buenos Aires",
        status=LeadStatus.SCORED,
        score=80.0,
        llm_summary="Already analyzed",
        llm_quality="high",
    )
    db.add(lead)
    db.commit()

    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with patch("app.workers.research_tasks.task_research_lead.delay") as mock_delay:
        from app.workers.pipeline_tasks import task_analyze_lead
        result = task_analyze_lead(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )
        assert result["status"] == "skipped"
        assert result["quality"] == "high"
        mock_delay.assert_called_once_with(
            str(lead.id), pipeline_run_id, correlation_id,
        )


def test_analyze_skip_non_high_chains_to_draft(db):
    """task_analyze_lead must chain to draft when skipping a non-HIGH lead."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Chain Analyze MEDIUM",
        city="Buenos Aires",
        status=LeadStatus.SCORED,
        score=45.0,
        llm_summary="Already analyzed",
        llm_quality="medium",
    )
    db.add(lead)
    db.commit()

    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with patch("app.workers.pipeline_tasks.task_generate_draft.delay") as mock_delay:
        from app.workers.pipeline_tasks import task_analyze_lead
        result = task_analyze_lead(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )
        assert result["status"] == "skipped"
        assert result["quality"] == "medium"
        mock_delay.assert_called_once_with(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )
