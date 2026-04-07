"""Pydantic response schemas for the /batch-reviews API endpoints."""

from typing import Any

from pydantic import BaseModel


class BatchReviewSummaryItem(BaseModel):
    id: str
    trigger_reason: str | None
    batch_size: int | None
    status: str | None
    reviewer_verdict: str | None
    strategy_brief: str | None
    proposals_count: int
    proposals_pending: int
    created_at: str | None


class ProposalItem(BaseModel):
    id: str
    category: str | None
    description: str | None
    impact: str | None
    confidence: str | None
    evidence_summary: str | None
    status: str | None
    approved_by: str | None
    applied_at: str | None


class BatchReviewDetailResponse(BaseModel):
    id: str
    trigger_reason: str | None
    batch_size: int | None
    period_start: str | None
    period_end: str | None
    status: str | None
    executor_draft: str | None
    reviewer_verdict: str | None
    reviewer_notes: str | None
    strategy_brief: str | None
    metrics_json: dict[str, Any] | None
    created_at: str | None
    proposals: list[ProposalItem]


class TriggerBatchReviewResponse(BaseModel):
    ok: bool
    task_id: str
    message: str


class ProposalActionResponse(BaseModel):
    id: str
    status: str | None
    approved_by: str | None = None
    applied_at: str | None = None
