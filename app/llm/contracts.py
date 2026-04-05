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


class ReviewCorrectionItem(BaseModel):
    """Structured correction from reviewer — enables aggregation and learning."""

    model_config = ConfigDict(extra="ignore")

    category: Literal[
        "tone", "cta", "personalization", "length",
        "accuracy", "relevance", "format", "language",
    ]
    severity: Literal["critical", "important", "suggestion"] = "suggestion"
    issue: str
    suggestion: str | None = None


class OutreachDraftReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["approve", "revise", "skip"]
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggested_changes: list[str] = Field(default_factory=list)
    corrections: list[ReviewCorrectionItem] = Field(default_factory=list)
    revised_subject: str | None = None
    revised_body: str | None = None


class LeadReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["priority", "worth_follow_up", "not_now"]
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    recommended_action: str
    watchouts: list[str] = Field(default_factory=list)
    corrections: list[ReviewCorrectionItem] = Field(default_factory=list)


class ReplyClassificationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: Literal[
        "interested",
        "not_interested",
        "neutral",
        "asked_for_quote",
        "asked_for_meeting",
        "asked_for_more_info",
        "wrong_contact",
        "out_of_office",
        "spam_or_irrelevant",
        "needs_human_review",
    ]
    summary: str
    confidence: float = Field(ge=0, le=1)
    next_action_suggestion: str
    should_escalate_reviewer: bool


class InboundReplyReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["reply_now", "consider_reply", "ignore", "escalate_human"]
    confidence: Literal["high", "medium", "low"]
    reasoning: str
    recommended_action: str
    suggested_response_angle: str | None = None
    watchouts: list[str] = Field(default_factory=list)


class ReplyAssistantDraftResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subject: str
    body: str
    summary: str | None = None
    suggested_tone: str | None = None
    should_escalate_reviewer: bool


class ReplyAssistantDraftReviewResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    feedback: str
    suggested_edits: list[str] = Field(default_factory=list)
    recommended_action: Literal[
        "use_as_is",
        "edit_before_sending",
        "escalate_to_reviewer",
        "skip_reply",
    ]
    should_use_as_is: bool
    should_edit: bool
    should_escalate: bool


class WhatsAppDraftResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body: str


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
    corrections: list[ReviewCorrectionItem] = Field(default_factory=list)


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


# ── Batch Review Contracts ──────────────────────────────────────────


class ProposalItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str
    description: str
    impact: Literal["high", "medium", "low"] = "medium"
    confidence: Literal["high", "medium", "low"] = "medium"
    evidence: str = ""


class BatchReviewSynthesisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strategy_brief: str
    proposals: list[ProposalItem] = Field(default_factory=list)


class BatchReviewValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    validated_brief: str
    adjusted_proposals: list[ProposalItem] = Field(default_factory=list)
    reviewer_notes: str = ""


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
