"""LLM cost estimation — USD per 1K tokens by model.

For local Ollama models, "cost" is the GPU/CPU compute value you would
otherwise pay a cloud provider for equivalent throughput. The numbers
below are rough public benchmarks, not contractual pricing. They exist
to give the operator a $/lead signal and to back the daily_usd_budget
kill-switch. Override per-model by editing this module when you change
fleet composition.

Unknown models return 0.0 cost (conservative: we prefer silent success
over blocking unknown invocations).
"""

from __future__ import annotations

from typing import Final

# Price per 1,000 tokens (USD).
# Local Ollama proxy values — approximate cloud equivalents for the models
# Scouter runs today. Adjust as pricing or models shift.
PRICING_PER_MODEL: Final[dict[str, tuple[float, float]]] = {
    # (prompt_per_1k, completion_per_1k)
    "hermes3:8b": (0.0002, 0.0004),
    "qwen3.5:9b": (0.0002, 0.0004),
    "qwen3.5:27b": (0.0008, 0.0016),
    # Known external aliases; keep parity with Ollama model names
    "qwen2.5:9b": (0.0002, 0.0004),
    "qwen2.5:27b": (0.0008, 0.0016),
}


def estimate_usd_cost(
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float:
    """Compute a USD cost estimate for a single LLM invocation.

    - Returns 0.0 if model is None, unknown, or both token counts are None.
    - Treats missing token counts as 0 (conservative).
    - Rounds to 6 decimals (sub-millicent precision).
    """
    if not model:
        return 0.0
    pricing = PRICING_PER_MODEL.get(model)
    if pricing is None:
        return 0.0

    prompt_tokens = prompt_tokens or 0
    completion_tokens = completion_tokens or 0
    if prompt_tokens == 0 and completion_tokens == 0:
        return 0.0

    prompt_rate, completion_rate = pricing
    total = (prompt_tokens / 1000.0) * prompt_rate + (completion_tokens / 1000.0) * completion_rate
    return round(total, 6)
