"""Pydantic response schemas for the /performance API endpoints."""

from typing import Any

from pydantic import BaseModel


class AIHealthResponse(BaseModel):
    approval_rate: float
    fallback_rate: float
    avg_latency_ms: int | None
    invocations_24h: int


class SignalWonItem(BaseModel):
    signal: str
    count: int


class OutcomeAnalyticsResponse(BaseModel):
    total_won: int
    total_lost: int
    by_industry: list[dict[str, Any]]
    by_quality: list[dict[str, Any]]
    top_signals_won: list[SignalWonItem]


class SignalCorrelationItem(BaseModel):
    signal: str
    won: int
    lost: int
    total: int
    win_rate: float


class ScoringRecommendationItem(BaseModel):
    type: str
    description: str
    evidence: str
    action: str


class AnalysisSummaryResponse(BaseModel):
    summary: dict[str, Any]
    signal_correlations: list[dict[str, Any]]
    quality_accuracy: list[dict[str, Any]]
    industry_performance: list[dict[str, Any]]


class InvestigationDetailResponse(BaseModel):
    id: str
    lead_id: str
    agent_model: str | None
    tool_calls: list[Any] | None
    pages_visited: list[Any] | None
    findings: Any = None
    loops_used: int | None
    duration_ms: int | None
    error: str | None
    created_at: str | None
