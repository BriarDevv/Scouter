from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from app.llm.contracts import (
    BatchReviewSynthesisResult,
    BatchReviewValidationResult,
    BusinessSummaryResult,
    CommercialBriefResult,
    CommercialBriefReviewResult,
    DossierResult,
    GrowthDecision,
    InboundReplyReviewResult,
    LeadQualityResult,
    LeadReviewResult,
    OutreachDraftResult,
    OutreachDraftReviewResult,
    ReplyAssistantDraftResult,
    ReplyAssistantDraftReviewResult,
    ReplyClassificationResult,
    WhatsAppDraftResult,
)
from app.llm.prompts import (
    BATCH_REVIEW_SYNTHESIS_DATA,
    BATCH_REVIEW_SYNTHESIS_SYSTEM,
    BATCH_REVIEW_VALIDATION_DATA,
    BATCH_REVIEW_VALIDATION_SYSTEM,
    CLASSIFY_INBOUND_REPLY_DATA,
    CLASSIFY_INBOUND_REPLY_SYSTEM,
    COMMERCIAL_BRIEF_DATA,
    COMMERCIAL_BRIEF_SYSTEM,
    DOSSIER_DATA,
    DOSSIER_SYSTEM,
    EVALUATE_LEAD_QUALITY_DATA,
    EVALUATE_LEAD_QUALITY_SYSTEM,
    GENERATE_OUTREACH_EMAIL_DATA,
    GENERATE_OUTREACH_EMAIL_SYSTEM,
    GENERATE_REPLY_ASSISTANT_DRAFT_DATA,
    GENERATE_REPLY_ASSISTANT_DRAFT_SYSTEM,
    GENERATE_WHATSAPP_DRAFT_DATA,
    GENERATE_WHATSAPP_DRAFT_SYSTEM,
    GROWTH_DECISION_DATA,
    GROWTH_DECISION_SYSTEM,
    REVIEW_COMMERCIAL_BRIEF_DATA,
    REVIEW_COMMERCIAL_BRIEF_SYSTEM,
    REVIEW_INBOUND_REPLY_DATA,
    REVIEW_INBOUND_REPLY_SYSTEM,
    REVIEW_LEAD_DATA,
    REVIEW_LEAD_SYSTEM,
    REVIEW_OUTREACH_DRAFT_DATA,
    REVIEW_OUTREACH_DRAFT_SYSTEM,
    REVIEW_REPLY_ASSISTANT_DRAFT_DATA,
    REVIEW_REPLY_ASSISTANT_DRAFT_SYSTEM,
    SUMMARIZE_BUSINESS_DATA,
    SUMMARIZE_BUSINESS_SYSTEM,
)


@dataclass(frozen=True, slots=True)
class PromptDefinition[SchemaT: BaseModel]:
    prompt_id: str
    prompt_version: str
    owner: str
    system_prompt: str
    user_prompt_template: str
    response_model: type[SchemaT]
    tags: tuple[str, ...] = field(default_factory=tuple)

    def render_user_prompt(self, **kwargs: object) -> str:
        return self.user_prompt_template.format(**kwargs)


LEAD_QUALITY_PROMPT = PromptDefinition(
    prompt_id="lead_quality.evaluate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=EVALUATE_LEAD_QUALITY_SYSTEM,
    user_prompt_template=EVALUATE_LEAD_QUALITY_DATA,
    response_model=LeadQualityResult,
    tags=("lead", "qualification"),
)


BUSINESS_SUMMARY_PROMPT = PromptDefinition(
    prompt_id="business_summary.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=SUMMARIZE_BUSINESS_SYSTEM,
    user_prompt_template=SUMMARIZE_BUSINESS_DATA,
    response_model=BusinessSummaryResult,
    tags=("lead", "summary"),
)


OUTREACH_DRAFT_PROMPT = PromptDefinition(
    prompt_id="outreach_draft.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=GENERATE_OUTREACH_EMAIL_SYSTEM,
    user_prompt_template=GENERATE_OUTREACH_EMAIL_DATA,
    response_model=OutreachDraftResult,
    tags=("lead", "outreach"),
)


OUTREACH_DRAFT_REVIEW_PROMPT = PromptDefinition(
    prompt_id="outreach_draft.review",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=REVIEW_OUTREACH_DRAFT_SYSTEM,
    user_prompt_template=REVIEW_OUTREACH_DRAFT_DATA,
    response_model=OutreachDraftReviewResult,
    tags=("lead", "outreach", "review"),
)


LEAD_REVIEW_PROMPT = PromptDefinition(
    prompt_id="lead_review.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=REVIEW_LEAD_SYSTEM,
    user_prompt_template=REVIEW_LEAD_DATA,
    response_model=LeadReviewResult,
    tags=("lead", "review"),
)


REPLY_ASSISTANT_DRAFT_PROMPT = PromptDefinition(
    prompt_id="reply_assistant_draft.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=GENERATE_REPLY_ASSISTANT_DRAFT_SYSTEM,
    user_prompt_template=GENERATE_REPLY_ASSISTANT_DRAFT_DATA,
    response_model=ReplyAssistantDraftResult,
    tags=("inbox", "reply_assistant"),
)


REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT = PromptDefinition(
    prompt_id="reply_assistant_draft.review",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=REVIEW_REPLY_ASSISTANT_DRAFT_SYSTEM,
    user_prompt_template=REVIEW_REPLY_ASSISTANT_DRAFT_DATA,
    response_model=ReplyAssistantDraftReviewResult,
    tags=("inbox", "reply_assistant", "review"),
)


WHATSAPP_DRAFT_PROMPT = PromptDefinition(
    prompt_id="whatsapp_draft.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=GENERATE_WHATSAPP_DRAFT_SYSTEM,
    user_prompt_template=GENERATE_WHATSAPP_DRAFT_DATA,
    response_model=WhatsAppDraftResult,
    tags=("lead", "outreach", "whatsapp"),
)


DOSSIER_PROMPT = PromptDefinition(
    prompt_id="dossier.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=DOSSIER_SYSTEM,
    user_prompt_template=DOSSIER_DATA,
    response_model=DossierResult,
    tags=("lead", "research", "dossier"),
)


INBOUND_REPLY_CLASSIFICATION_PROMPT = PromptDefinition(
    prompt_id="inbound_reply.classify",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=CLASSIFY_INBOUND_REPLY_SYSTEM,
    user_prompt_template=CLASSIFY_INBOUND_REPLY_DATA,
    response_model=ReplyClassificationResult,
    tags=("inbox", "classification"),
)


INBOUND_REPLY_REVIEW_PROMPT = PromptDefinition(
    prompt_id="inbound_reply.review",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=REVIEW_INBOUND_REPLY_SYSTEM,
    user_prompt_template=REVIEW_INBOUND_REPLY_DATA,
    response_model=InboundReplyReviewResult,
    tags=("inbox", "review"),
)


COMMERCIAL_BRIEF_PROMPT = PromptDefinition(
    prompt_id="commercial_brief.generate",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=COMMERCIAL_BRIEF_SYSTEM,
    user_prompt_template=COMMERCIAL_BRIEF_DATA,
    response_model=CommercialBriefResult,
    tags=("lead", "brief"),
)


COMMERCIAL_BRIEF_REVIEW_PROMPT = PromptDefinition(
    prompt_id="commercial_brief.review",
    prompt_version="v2",
    owner="app.llm.client",
    system_prompt=REVIEW_COMMERCIAL_BRIEF_SYSTEM,
    user_prompt_template=REVIEW_COMMERCIAL_BRIEF_DATA,
    response_model=CommercialBriefReviewResult,
    tags=("lead", "brief", "review"),
)


GROWTH_DECISION_PROMPT = PromptDefinition(
    prompt_id="growth_decision.generate",
    prompt_version="v1",
    owner="app.services.growth.growth_service",
    system_prompt=GROWTH_DECISION_SYSTEM,
    user_prompt_template=GROWTH_DECISION_DATA,
    response_model=GrowthDecision,
    tags=("growth", "agent"),
)


PROMPT_REGISTRY: dict[str, PromptDefinition[BaseModel]] = {
    BUSINESS_SUMMARY_PROMPT.prompt_id: BUSINESS_SUMMARY_PROMPT,
    LEAD_QUALITY_PROMPT.prompt_id: LEAD_QUALITY_PROMPT,
    OUTREACH_DRAFT_PROMPT.prompt_id: OUTREACH_DRAFT_PROMPT,
    OUTREACH_DRAFT_REVIEW_PROMPT.prompt_id: OUTREACH_DRAFT_REVIEW_PROMPT,
    LEAD_REVIEW_PROMPT.prompt_id: LEAD_REVIEW_PROMPT,
    REPLY_ASSISTANT_DRAFT_PROMPT.prompt_id: REPLY_ASSISTANT_DRAFT_PROMPT,
    REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT.prompt_id: REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT,
    WHATSAPP_DRAFT_PROMPT.prompt_id: WHATSAPP_DRAFT_PROMPT,
    DOSSIER_PROMPT.prompt_id: DOSSIER_PROMPT,
    INBOUND_REPLY_CLASSIFICATION_PROMPT.prompt_id: INBOUND_REPLY_CLASSIFICATION_PROMPT,
    INBOUND_REPLY_REVIEW_PROMPT.prompt_id: INBOUND_REPLY_REVIEW_PROMPT,
    COMMERCIAL_BRIEF_PROMPT.prompt_id: COMMERCIAL_BRIEF_PROMPT,
    COMMERCIAL_BRIEF_REVIEW_PROMPT.prompt_id: COMMERCIAL_BRIEF_REVIEW_PROMPT,
    GROWTH_DECISION_PROMPT.prompt_id: GROWTH_DECISION_PROMPT,
    "batch_review.synthesis": PromptDefinition(
        prompt_id="batch_review.synthesis",
        prompt_version="v1",
        owner="app.services.pipeline.batch_review_service",
        system_prompt=BATCH_REVIEW_SYNTHESIS_SYSTEM,
        user_prompt_template=BATCH_REVIEW_SYNTHESIS_DATA,
        response_model=BatchReviewSynthesisResult,
    ),
    "batch_review.validation": PromptDefinition(
        prompt_id="batch_review.validation",
        prompt_version="v1",
        owner="app.services.pipeline.batch_review_service",
        system_prompt=BATCH_REVIEW_VALIDATION_SYSTEM,
        user_prompt_template=BATCH_REVIEW_VALIDATION_DATA,
        response_model=BatchReviewValidationResult,
    ),
}
