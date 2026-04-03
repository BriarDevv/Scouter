from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from app.llm.contracts import (
    CommercialBriefResult,
    CommercialBriefReviewResult,
    LeadQualityResult,
)
from app.llm.prompts import (
    COMMERCIAL_BRIEF_DATA,
    COMMERCIAL_BRIEF_SYSTEM,
    EVALUATE_LEAD_QUALITY_DATA,
    EVALUATE_LEAD_QUALITY_SYSTEM,
    REVIEW_COMMERCIAL_BRIEF_DATA,
    REVIEW_COMMERCIAL_BRIEF_SYSTEM,
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
    LEAD_QUALITY_PROMPT.prompt_id: LEAD_QUALITY_PROMPT,
    COMMERCIAL_BRIEF_PROMPT.prompt_id: COMMERCIAL_BRIEF_PROMPT,
    COMMERCIAL_BRIEF_REVIEW_PROMPT.prompt_id: COMMERCIAL_BRIEF_REVIEW_PROMPT,
}
