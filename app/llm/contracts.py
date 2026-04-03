from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.llm.types import LLMInvocationStatus


class LeadQualityResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quality: Literal["high", "medium", "low", "unknown"]
    reasoning: str
    suggested_angle: str


class BusinessSummaryResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str


class OutreachDraftResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject: str
    body: str


class LeadReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["priority", "worth_follow_up", "not_now"]
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    recommended_action: str
    watchouts: list[str] = Field(default_factory=list)


class DossierResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    business_description: str
    digital_maturity: Literal["none", "basic", "intermediate", "advanced", "unknown"]
    key_findings: list[str] = Field(default_factory=list)
    improvement_opportunities: list[str] = Field(default_factory=list)
    overall_assessment: str


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
