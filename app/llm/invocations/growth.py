from __future__ import annotations

import json

from app.llm.contracts import GrowthAction, GrowthDecision
from app.llm.invocations.support import get_client_module
from app.llm.prompt_registry import GROWTH_DECISION_PROMPT
from app.llm.roles import LLMRole


def _growth_decision_fallback(state_summary: dict) -> GrowthDecision:
    """Conservative default: expand the first known territory, if any."""
    performance = state_summary.get("territory_performance") or []
    territory_id: str | None = None
    if performance:
        first = performance[0]
        if isinstance(first, dict):
            territory_id = first.get("territory_id")

    return GrowthDecision(
        decision="expand",
        reason="LLM unavailable; defaulting to geographic expansion of the first territory.",
        action=GrowthAction(
            territory_id=territory_id,
            new_cities=state_summary.get("available_cities", [])[:3] or None,
        ),
        confidence=0.2,
        next_step=(
            "Review suggested cities and apply geographic expansion to the first active territory."
        ),
    )


def _as_json(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


def decide_growth_strategy(
    state_summary: dict,
    role: LLMRole | str = LLMRole.REVIEWER,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
) -> GrowthDecision:
    """Ask the Growth Intelligence Agent to pick the next expansion strategy.

    The reviewer model (qwen3.5:27b) handles this because growth decisions
    benefit from the strongest reasoning quality available.
    """
    client_module = get_client_module()
    prompt_args = {
        "saturated_territories": _as_json(state_summary.get("saturated_territories", [])),
        "territory_performance": _as_json(state_summary.get("territory_performance", [])),
        "available_cities": _as_json(state_summary.get("available_cities", [])),
        "current_categories": _as_json(state_summary.get("current_categories", [])),
        "pipeline_activity": _as_json(state_summary.get("pipeline_activity", {})),
    }

    result = client_module.invoke_structured(
        function_name="decide_growth_strategy",
        prompt=GROWTH_DECISION_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _growth_decision_fallback(state_summary),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )

    if result.parsed is None:
        return _growth_decision_fallback(state_summary)
    return result.parsed
