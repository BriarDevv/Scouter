"""Tests for pipeline context service — append, read, format, size limits."""

import uuid

from app.models.lead import Lead
from app.models.task_tracking import PipelineRun
from app.services.pipeline.context_service import (
    append_step_context,
    format_context_for_prompt,
    get_step_context,
)


def _make_lead(db) -> Lead:
    lead = Lead(business_name="Context Test", city="CABA", industry="Cafe")
    db.add(lead)
    db.flush()
    return lead


def _make_run(db, lead_id=None) -> PipelineRun:
    if not lead_id:
        lead_id = _make_lead(db).id
    run = PipelineRun(lead_id=lead_id, correlation_id=str(uuid.uuid4()), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def test_append_and_get_step_context(db):
    run = _make_run(db)
    append_step_context(db, run.id, "enrichment", {"signals": ["no_website"], "email_found": True})
    append_step_context(db, run.id, "scoring", {"score": 85, "signal_count": 3})

    ctx = get_step_context(db, run.id)
    assert "enrichment" in ctx
    assert "scoring" in ctx
    assert ctx["enrichment"]["signals"] == ["no_website"]
    assert ctx["scoring"]["score"] == 85


def test_append_overwrites_same_step(db):
    run = _make_run(db)
    append_step_context(db, run.id, "scoring", {"score": 50})
    append_step_context(db, run.id, "scoring", {"score": 85})

    ctx = get_step_context(db, run.id)
    assert ctx["scoring"]["score"] == 85


def test_append_truncates_large_step(db):
    run = _make_run(db)
    large = {"data": "x" * 3000}
    append_step_context(db, run.id, "big_step", large)

    ctx = get_step_context(db, run.id)
    assert ctx["big_step"]["truncated"] is True
    assert "summary" in ctx["big_step"]


def test_append_rejects_when_total_too_large(db):
    run = _make_run(db)
    for i in range(10):
        append_step_context(db, run.id, f"step_{i}", {"data": "x" * 1500})

    ctx = get_step_context(db, run.id)
    assert len(str(ctx)) < 20000


def test_get_context_missing_run(db):
    ctx = get_step_context(db, uuid.uuid4())
    assert ctx == {}


def test_append_missing_run_does_not_crash(db):
    append_step_context(db, uuid.uuid4(), "test", {"x": 1})


def test_format_empty_context():
    assert format_context_for_prompt({}) == ""


def test_format_enrichment_context():
    ctx = {"enrichment": {"signals": ["no_website", "weak_seo"], "email_found": True}}
    result = format_context_for_prompt(ctx)
    assert "no_website" in result
    assert "email=yes" in result


def test_format_full_pipeline_context():
    ctx = {
        "enrichment": {"signals": ["no_website"], "email_found": False},
        "scoring": {"score": 92},
        "analysis": {"quality": "high", "reasoning": "Strong signals", "suggested_angle": "web redesign"},
        "scout": {"findings": {"opportunity": "No web presence, great fit"}, "pages_visited": [{"url": "https://example.com"}]},
        "brief": {"opportunity_score": 9, "budget_tier": "high", "recommended_contact_method": "whatsapp", "recommended_angle": "Modern web presence"},
        "brief_review": {"approved": True, "verdict_reasoning": "Solid brief"},
    }
    result = format_context_for_prompt(ctx)
    assert "Score: 92/100" in result
    assert "high" in result
    assert "web redesign" in result
    assert "Scout findings:" in result
    assert "Brief:" in result
    assert "approved" in result


def test_format_truncates_at_max_chars():
    ctx = {
        "enrichment": {"signals": ["s"] * 200, "email_found": True},
        "scoring": {"score": 50},
        "analysis": {"quality": "medium", "reasoning": "A" * 1000},
    }
    result = format_context_for_prompt(ctx, max_chars=200)
    assert len(result) <= 203
    assert result.endswith("...")
