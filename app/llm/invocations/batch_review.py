"""Batch review invocations — Executor synthesis + Reviewer validation."""

from __future__ import annotations

import json

from app.llm.contracts import BatchReviewSynthesisResult, BatchReviewValidationResult
from app.llm.invocations.support import get_client_module
from app.llm.prompt_registry import PROMPT_REGISTRY
from app.llm.roles import LLMRole


def _synthesis_fallback() -> BatchReviewSynthesisResult:
    return BatchReviewSynthesisResult(
        strategy_brief="Synthesis unavailable — Executor did not produce a valid response.",
        proposals=[],
    )


def _validation_fallback() -> BatchReviewValidationResult:
    return BatchReviewValidationResult(
        validated_brief="Validation unavailable — Reviewer did not produce a valid response.",
        adjusted_proposals=[],
        reviewer_notes="Reviewer fallback activated.",
    )


def generate_batch_synthesis_structured(
    *,
    batch_size: int,
    period_start: str,
    period_end: str,
    trigger_reason: str,
    metrics_json: str,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client = get_client_module()
    prompt = PROMPT_REGISTRY["batch_review.synthesis"]
    return client.invoke_structured(
        function_name="batch_review_synthesis",
        prompt=prompt,
        prompt_args={
            "batch_size": batch_size,
            "period_start": period_start,
            "period_end": period_end,
            "trigger_reason": trigger_reason,
            "metrics_json": metrics_json,
        },
        role=LLMRole.EXECUTOR,
        fallback_factory=_synthesis_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def validate_batch_review_structured(
    *,
    executor_draft: str,
    metrics_json: str,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client = get_client_module()
    prompt = PROMPT_REGISTRY["batch_review.validation"]
    return client.invoke_structured(
        function_name="batch_review_validation",
        prompt=prompt,
        prompt_args={
            "executor_draft": executor_draft,
            "metrics_json": metrics_json,
        },
        role=LLMRole.REVIEWER,
        fallback_factory=_validation_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )
