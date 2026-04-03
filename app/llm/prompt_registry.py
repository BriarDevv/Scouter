from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from app.llm.contracts import (
    BusinessSummaryResult,
    CommercialBriefResult,
    CommercialBriefReviewResult,
    DossierResult,
    LeadQualityResult,
    LeadReviewResult,
    OutreachDraftResult,
)
from app.llm.prompts import (
    COMMERCIAL_BRIEF_DATA,
    COMMERCIAL_BRIEF_SYSTEM,
    DOSSIER_DATA,
    DOSSIER_SYSTEM,
    EVALUATE_LEAD_QUALITY_DATA,
    EVALUATE_LEAD_QUALITY_SYSTEM,
    GENERATE_OUTREACH_EMAIL_DATA,
    GENERATE_OUTREACH_EMAIL_SYSTEM,
    REVIEW_COMMERCIAL_BRIEF_DATA,
    REVIEW_COMMERCIAL_BRIEF_SYSTEM,
    REVIEW_LEAD_DATA,
    REVIEW_LEAD_SYSTEM,
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
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=EVALUATE_LEAD_QUALITY_SYSTEM,
    user_prompt_template=EVALUATE_LEAD_QUALITY_DATA,
    response_model=LeadQualityResult,
    tags=("lead", "qualification"),
)


BUSINESS_SUMMARY_PROMPT = PromptDefinition(
    prompt_id="business_summary.generate",
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=SUMMARIZE_BUSINESS_SYSTEM,
    user_prompt_template=SUMMARIZE_BUSINESS_DATA,
    response_model=BusinessSummaryResult,
    tags=("lead", "summary"),
)


OUTREACH_DRAFT_PROMPT = PromptDefinition(
    prompt_id="outreach_draft.generate",
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=GENERATE_OUTREACH_EMAIL_SYSTEM,
    user_prompt_template=GENERATE_OUTREACH_EMAIL_DATA,
    response_model=OutreachDraftResult,
    tags=("lead", "outreach"),
)


LEAD_REVIEW_PROMPT = PromptDefinition(
    prompt_id="lead_review.generate",
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=REVIEW_LEAD_SYSTEM,
    user_prompt_template=REVIEW_LEAD_DATA,
    response_model=LeadReviewResult,
    tags=("lead", "review"),
)


DOSSIER_PROMPT = PromptDefinition(
    prompt_id="dossier.generate",
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=DOSSIER_SYSTEM,
    user_prompt_template=DOSSIER_DATA,
    response_model=DossierResult,
    tags=("lead", "research", "dossier"),
)


COMMERCIAL_BRIEF_PROMPT = PromptDefinition(
    prompt_id="commercial_brief.generate",
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=COMMERCIAL_BRIEF_SYSTEM,
    user_prompt_template=COMMERCIAL_BRIEF_DATA,
    response_model=CommercialBriefResult,
    tags=("lead", "brief"),
)


COMMERCIAL_BRIEF_REVIEW_PROMPT = PromptDefinition(
    prompt_id="commercial_brief.review",
    prompt_version="v1",
    owner="app.llm.client",
    system_prompt=REVIEW_COMMERCIAL_BRIEF_SYSTEM,
    user_prompt_template=REVIEW_COMMERCIAL_BRIEF_DATA,
    response_model=CommercialBriefReviewResult,
    tags=("lead", "brief", "review"),
)


PROMPT_REGISTRY: dict[str, PromptDefinition[BaseModel]] = {
    BUSINESS_SUMMARY_PROMPT.prompt_id: BUSINESS_SUMMARY_PROMPT,
    LEAD_QUALITY_PROMPT.prompt_id: LEAD_QUALITY_PROMPT,
    OUTREACH_DRAFT_PROMPT.prompt_id: OUTREACH_DRAFT_PROMPT,
    LEAD_REVIEW_PROMPT.prompt_id: LEAD_REVIEW_PROMPT,
    DOSSIER_PROMPT.prompt_id: DOSSIER_PROMPT,
    COMMERCIAL_BRIEF_PROMPT.prompt_id: COMMERCIAL_BRIEF_PROMPT,
    COMMERCIAL_BRIEF_REVIEW_PROMPT.prompt_id: COMMERCIAL_BRIEF_REVIEW_PROMPT,
}
