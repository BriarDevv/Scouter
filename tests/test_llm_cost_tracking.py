"""Regression tests for LLM cost tracking + daily budget kill-switch.

Closes docs/roadmaps/post-hardening-plan.md Item 1. Three surfaces:

1. app/llm/cost_estimation.py — pure functions, no DB
2. app/services/pipeline/cost_gate.py — sums today's usd_cost_estimated and
   compares to OperationalSettings.daily_usd_budget
3. task_full_pipeline — invokes the cost gate and skips dispatch if
   over-budget, emitting a critical notification
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from app.llm.cost_estimation import PRICING_PER_MODEL, estimate_usd_cost
from app.models.llm_invocation import LLMInvocation, LLMInvocationStatus
from app.models.settings import OperationalSettings
from app.services.pipeline.cost_gate import check_daily_budget, get_today_cost_usd

# ---------------------------------------------------------------------------
# Pure estimate_usd_cost
# ---------------------------------------------------------------------------


def test_estimate_usd_cost_known_model_positive():
    # qwen3.5:9b → (0.0002, 0.0004). 1000 in + 500 out → 0.0002 + 0.0002 = 0.0004
    cost = estimate_usd_cost("qwen3.5:9b", prompt_tokens=1000, completion_tokens=500)
    assert cost > 0
    # Sanity: within ballpark of manual calc
    assert 0.0003 <= cost <= 0.0005


def test_estimate_usd_cost_unknown_model_returns_zero():
    assert estimate_usd_cost("made-up-model:999b", 10000, 10000) == 0.0


def test_estimate_usd_cost_missing_tokens_returns_zero():
    assert estimate_usd_cost("qwen3.5:9b", None, None) == 0.0
    assert estimate_usd_cost("qwen3.5:9b", 0, 0) == 0.0


def test_estimate_usd_cost_no_model_returns_zero():
    assert estimate_usd_cost(None, 100, 100) == 0.0


def test_pricing_per_model_has_no_negative_rates():
    """Defensive: guard the table against typo'd negative rates."""
    for model, (p, c) in PRICING_PER_MODEL.items():
        assert p >= 0, f"{model} has negative prompt rate"
        assert c >= 0, f"{model} has negative completion rate"


# ---------------------------------------------------------------------------
# Cost gate
# ---------------------------------------------------------------------------


def _insert_invocation_today(db, *, cost_usd: float) -> None:
    inv = LLMInvocation(
        function_name="fn",
        prompt_id="p",
        prompt_version="v1",
        role="executor",
        status=LLMInvocationStatus.SUCCEEDED,
        model="qwen3.5:9b",
        prompt_tokens=100,
        completion_tokens=50,
        usd_cost_estimated=cost_usd,
    )
    db.add(inv)
    db.commit()
    # server_default=func.now() already sets created_at; no need to override.
    db.refresh(inv)


def test_check_daily_budget_returns_true_when_budget_none(db):
    ops = db.get(OperationalSettings, 1)
    ops.daily_usd_budget = None
    db.commit()
    assert check_daily_budget(db) is True


def test_check_daily_budget_returns_false_when_today_over_budget(db):
    ops = db.get(OperationalSettings, 1)
    ops.daily_usd_budget = 0.001  # 0.1 cent
    db.commit()
    _insert_invocation_today(db, cost_usd=0.002)  # 0.2 cent — over budget
    assert check_daily_budget(db) is False


def test_check_daily_budget_returns_true_when_today_under_budget(db):
    ops = db.get(OperationalSettings, 1)
    ops.daily_usd_budget = 1.0
    db.commit()
    _insert_invocation_today(db, cost_usd=0.05)
    assert check_daily_budget(db) is True


def test_get_today_cost_usd_sums_only_today(db):
    _insert_invocation_today(db, cost_usd=0.10)
    _insert_invocation_today(db, cost_usd=0.20)
    # Backdate one to yesterday — should NOT count
    backdated = LLMInvocation(
        function_name="fn",
        prompt_id="p",
        prompt_version="v1",
        role="executor",
        status=LLMInvocationStatus.SUCCEEDED,
        model="qwen3.5:9b",
        usd_cost_estimated=0.50,
    )
    db.add(backdated)
    db.commit()
    db.refresh(backdated)
    backdated.created_at = datetime.now(UTC).replace(hour=0) - __import__("datetime").timedelta(
        days=1
    )
    db.commit()

    total = get_today_cost_usd(db)
    assert abs(total - 0.30) < 1e-6


# ---------------------------------------------------------------------------
# task_full_pipeline budget gate
# ---------------------------------------------------------------------------


def test_task_full_pipeline_skips_when_over_budget(db):
    from app.models.lead import Lead
    from app.workers.pipeline_tasks import task_full_pipeline

    ops = db.get(OperationalSettings, 1)
    ops.daily_usd_budget = 0.001
    db.commit()
    _insert_invocation_today(db, cost_usd=0.005)  # blow past budget

    lead = Lead(id=uuid.uuid4(), business_name="Over Budget Biz", city="BA", status="new")
    db.add(lead)
    db.commit()

    with patch("app.workers.pipeline_tasks.task_enrich_lead.delay") as mock_enrich_delay:
        result = task_full_pipeline(str(lead.id))

    assert result["status"] == "skipped"
    assert result["reason"] == "daily_budget_exceeded"
    mock_enrich_delay.assert_not_called()


def test_task_full_pipeline_dispatches_when_under_budget(db):
    from app.models.lead import Lead
    from app.workers.pipeline_tasks import task_full_pipeline

    ops = db.get(OperationalSettings, 1)
    ops.daily_usd_budget = 10.0
    db.commit()

    lead = Lead(id=uuid.uuid4(), business_name="Healthy Biz", city="BA", status="new")
    db.add(lead)
    db.commit()

    with patch("app.workers.pipeline_tasks.task_enrich_lead.delay") as mock_enrich_delay:
        result = task_full_pipeline(str(lead.id))

    assert result["status"] == "pipeline_started"
    mock_enrich_delay.assert_called_once()
