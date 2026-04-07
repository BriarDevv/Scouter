"""Tests for the performance API."""

from app.models.investigation_thread import InvestigationThread
from app.models.lead import Lead, LeadStatus


def test_get_ai_health_empty(client):
    resp = client.get("/api/v1/performance/ai-health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["invocations_24h"] == 0
    assert data["approval_rate"] == 0.0
    assert data["fallback_rate"] == 0.0
    assert data["avg_latency_ms"] is None


def test_get_ai_health_with_data(db, client):
    from app.models.llm_invocation import LLMInvocation, LLMInvocationStatus

    inv = LLMInvocation(
        function_name="test_fn",
        prompt_id="test_prompt",
        prompt_version="1.0",
        role="executor",
        model="test-model",
        status=LLMInvocationStatus.SUCCEEDED,
        fallback_used=False,
        degraded=False,
        parse_valid=True,
        latency_ms=150,
    )
    db.add(inv)
    db.commit()

    resp = client.get("/api/v1/performance/ai-health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["invocations_24h"] >= 1
    assert data["approval_rate"] > 0
    assert data["avg_latency_ms"] is not None


def test_get_outcome_analytics_empty(client):
    resp = client.get("/api/v1/performance/outcomes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_won"] == 0
    assert data["total_lost"] == 0


def test_get_signal_correlation_empty(client):
    resp = client.get("/api/v1/performance/outcomes/signals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_scoring_recommendations_empty(client):
    resp = client.get("/api/v1/performance/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) or isinstance(data, list)


def test_get_analysis_summary_empty(client):
    resp = client.get("/api/v1/performance/analysis/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "signal_correlations" in data
    assert "quality_accuracy" in data
    assert "industry_performance" in data


def test_get_investigation_not_found(client):
    resp = client.get("/api/v1/performance/investigations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_investigation_found(db, client):
    lead = Lead(
        business_name="Investigated Lead",
        city="Cordoba",
        status=LeadStatus.ENRICHED,
    )
    db.add(lead)
    db.flush()

    thread = InvestigationThread(
        lead_id=lead.id,
        agent_model="qwen3.5:9b",
        tool_calls_json=[{"tool": "google_search", "query": "test"}],
        pages_visited_json=["https://example.com"],
        findings_json={"has_website": True},
        loops_used=2,
        duration_ms=1500,
    )
    db.add(thread)
    db.commit()

    resp = client.get(f"/api/v1/performance/investigations/{lead.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lead_id"] == str(lead.id)
    assert data["agent_model"] == "qwen3.5:9b"
    assert data["loops_used"] == 2
    assert data["duration_ms"] == 1500
    assert len(data["tool_calls"]) == 1
    assert len(data["pages_visited"]) == 1


def test_get_industry_breakdown_empty(client):
    resp = client.get("/api/v1/performance/industry")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_city_breakdown_empty(client):
    resp = client.get("/api/v1/performance/city")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_source_performance_empty(client):
    resp = client.get("/api/v1/performance/source")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
