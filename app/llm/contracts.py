from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.llm.types import LLMInvocationStatus


class LeadQualityResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quality: Literal["high", "medium", "low", "unknown"]
    reasoning: str
    suggested_angle: str


class CommercialBriefResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    opportunity_score: float = Field(ge=0, le=100)
    estimated_scope: Literal[
        "landing",
        "institutional_web",
        "catalog",
        "ecommerce",
        "redesign",
        "automation",
        "branding_web",
    ]
    recommended_contact_method: Literal[
        "whatsapp",
        "email",
        "call",
        "demo_first",
        "manual_review",
    ]
    should_call: Literal["yes", "no", "maybe"]
    call_reason: str
    why_this_lead_matters: str
    main_business_signals: list[str] = Field(default_factory=list)
    main_digital_gaps: list[str] = Field(default_factory=list)
    recommended_angle: str
    demo_recommended: bool


class CommercialBriefReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    approved: bool
    feedback: str
    suggested_changes: str | None = None


class StructuredInvocationResult[ParsedT: BaseModel](BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: LLMInvocationStatus
    role: str
    model: str | None = None
    prompt_id: str
    prompt_version: str
    latency_ms: int | None = None
    fallback_used: bool = False
    degraded: bool = False
    parse_valid: bool = False
    raw_text: str | None = None
    parsed: ParsedT | None = None
    error: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class TextInvocationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: LLMInvocationStatus
    role: str
    model: str | None = None
    prompt_id: str
    prompt_version: str
    latency_ms: int | None = None
    fallback_used: bool = False
    degraded: bool = False
    parse_valid: bool = True
    raw_text: str | None = None
    text: str | None = None
    error: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
