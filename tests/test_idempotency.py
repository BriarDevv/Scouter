"""Tests for idempotency guards in pipeline tasks."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.lead import Lead, LeadStatus
from app.models.research_report import LeadResearchReport, ResearchStatus
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
        enriched_at=datetime.now(UTC),
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
        enriched_at=datetime.now(UTC),
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
        scored_at=datetime.now(UTC),
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
        scored_at=datetime.now(UTC),
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
            str(lead.id),
            pipeline_run_id,
            correlation_id,
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


def _make_lead_with_research(
    db, *, research_updated_at: datetime
) -> tuple[Lead, LeadResearchReport]:
    """Helper: create lead + completed research report pinned to a timestamp."""
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Research Idempotency Biz",
        city="Buenos Aires",
        status=LeadStatus.QUALIFIED,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    report = LeadResearchReport(
        lead_id=lead.id,
        status=ResearchStatus.COMPLETED,
    )
    db.add(report)
    db.commit()
    # Force updated_at retroactively (server_default set it to NOW; tests need control)
    report.updated_at = research_updated_at
    db.commit()
    db.refresh(report)
    return lead, report


def test_research_skips_when_recent_completed_report_exists(db):
    """task_research_lead must skip Scout+HTTP research if a completed report exists <24h."""
    lead, _report = _make_lead_with_research(
        db,
        research_updated_at=datetime.now(UTC) - timedelta(hours=1),
    )
    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with (
        patch("app.services.research.research_service.run_research") as mock_run_research,
        patch("app.workers.brief_tasks.task_generate_brief.delay") as mock_brief_delay,
    ):
        from app.workers.research_tasks import task_research_lead

        result = task_research_lead(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )

    assert result == {"status": "skipped", "reason": "recent_research_exists"}
    mock_run_research.assert_not_called()
    # Brief must still be chained so the pipeline doesn't stall.
    mock_brief_delay.assert_called_once_with(
        str(lead.id), pipeline_run_id, correlation_id=correlation_id
    )


def test_research_proceeds_when_recent_report_is_older_than_24h(db):
    """task_research_lead must proceed normally if existing report is stale (>24h)."""
    lead, _report = _make_lead_with_research(
        db,
        research_updated_at=datetime.now(UTC) - timedelta(hours=48),
    )
    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    # If the guard is correctly bypassed, run_research is invoked. We short-circuit
    # it with None to avoid running the real service.
    with (
        patch("app.services.research.research_service.run_research", return_value=None),
        patch("app.workers.brief_tasks.task_generate_brief.delay"),
        patch(
            "app.agent.research_agent.run_scout_investigation", side_effect=Exception("scout off")
        ),
    ):
        from app.workers.research_tasks import task_research_lead

        result = task_research_lead(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )

    # Guard bypassed -> result must NOT be the idempotent-skip payload.
    assert result != {"status": "skipped", "reason": "recent_research_exists"}


def _make_lead_with_brief(db, *, brief_status):
    """Helper: create lead + commercial brief in a given status."""
    from app.models.commercial_brief import CommercialBrief

    lead = Lead(
        id=uuid.uuid4(),
        business_name="Brief Idempotency Biz",
        city="Buenos Aires",
        status=LeadStatus.QUALIFIED,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    brief = CommercialBrief(lead_id=lead.id, status=brief_status)
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return lead, brief


def test_brief_generation_skipped_when_generated_brief_exists(db):
    """task_generate_brief must skip if CommercialBrief.status == GENERATED."""
    from app.models.commercial_brief import BriefStatus

    lead, _brief = _make_lead_with_brief(db, brief_status=BriefStatus.GENERATED)
    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with (
        patch("app.services.research.brief_service.generate_brief") as mock_generate,
        patch("app.workers.brief_tasks.task_review_brief.delay") as mock_review_delay,
    ):
        from app.workers.brief_tasks import task_generate_brief

        result = task_generate_brief(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )

    assert result["status"] == "skipped"
    assert result["reason"] == "brief_exists"
    assert result["existing_status"] == "generated"
    mock_generate.assert_not_called()
    # GENERATED brief -> chain to review
    mock_review_delay.assert_called_once_with(str(lead.id), pipeline_run_id)


def test_brief_generation_skipped_reviewed_brief_chains_to_draft(db):
    """task_generate_brief with REVIEWED brief must chain to draft directly."""
    from app.models.commercial_brief import BriefStatus

    lead, _brief = _make_lead_with_brief(db, brief_status=BriefStatus.REVIEWED)
    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with (
        patch("app.services.research.brief_service.generate_brief") as mock_generate,
        patch("app.workers.pipeline_tasks.task_generate_draft.delay") as mock_draft_delay,
    ):
        from app.workers.brief_tasks import task_generate_brief

        result = task_generate_brief(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )

    assert result["status"] == "skipped"
    assert result["existing_status"] == "reviewed"
    mock_generate.assert_not_called()
    mock_draft_delay.assert_called_once_with(str(lead.id), pipeline_run_id)


def test_brief_generation_proceeds_when_brief_is_pending(db):
    """task_generate_brief with PENDING brief must still invoke generate_brief."""
    from app.models.commercial_brief import BriefStatus

    lead, _brief = _make_lead_with_brief(db, brief_status=BriefStatus.PENDING)
    correlation_id = str(uuid.uuid4())
    pipeline_run_id = _create_pipeline_run(db, lead.id, correlation_id)

    with patch("app.services.research.brief_service.generate_brief", return_value=None):
        from app.workers.brief_tasks import task_generate_brief

        result = task_generate_brief(
            str(lead.id),
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
        )

    # Guard bypassed -> we hit the generate_brief path (which returns None here),
    # so result is the failure payload, NOT the idempotent-skip payload.
    assert result.get("reason") != "brief_exists"
