from __future__ import annotations

from app.llm.contracts import BusinessSummaryResult, LeadQualityResult, LeadReviewResult
from app.llm.invocations.support import format_signals, get_client_module
from app.llm.prompt_registry import BUSINESS_SUMMARY_PROMPT, LEAD_QUALITY_PROMPT, LEAD_REVIEW_PROMPT
from app.llm.roles import LLMRole
from app.llm.sanitizer import sanitize_field


def _business_summary_fallback(
    business_name: str,
    industry: str | None,
    city: str | None,
) -> BusinessSummaryResult:
    return BusinessSummaryResult(
        summary=(
            f"[LLM unavailable] {business_name} - "
            f"{industry or 'Unknown industry'} in {city or 'Unknown location'}"
        )
    )


def summarize_business_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    signals: list,
    role: LLMRole | str = LLMRole.EXECUTOR,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "signals": format_signals(signals),
    }
    return client_module.invoke_structured(
        function_name="summarize_business",
        prompt=BUSINESS_SUMMARY_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _business_summary_fallback(
            business_name,
            industry,
            city,
        ),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def summarize_business(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    signals: list,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> str:
    result = summarize_business_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        signals=signals,
        role=role,
    )
    if result.parsed is None:
        return _business_summary_fallback(business_name, industry, city).summary
    return result.parsed.summary


def _lead_quality_fallback() -> LeadQualityResult:
    return LeadQualityResult(
        quality="unknown",
        reasoning="LLM analysis unavailable",
        suggested_angle="General web development services",
    )


def evaluate_lead_quality_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    signals: list,
    score: float | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "signals": format_signals(signals),
        "score": score or 0,
    }
    return client_module.invoke_structured(
        function_name="evaluate_lead_quality",
        prompt=LEAD_QUALITY_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_lead_quality_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def evaluate_lead_quality(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    signals: list,
    score: float | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> dict:
    result = evaluate_lead_quality_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        signals=signals,
        score=score,
        role=role,
    )
    if result.parsed is None:
        return _lead_quality_fallback().model_dump()
    return result.parsed.model_dump()


def _lead_review_fallback() -> LeadReviewResult:
    return LeadReviewResult(
        verdict="worth_follow_up",
        confidence="low",
        reasoning="Reviewer analysis unavailable.",
        recommended_action="Review this lead manually before taking action.",
        watchouts=["Reviewer output unavailable"],
    )


def review_lead_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    score: float | None,
    role: LLMRole | str = LLMRole.REVIEWER,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "llm_summary": sanitize_field(llm_summary) or "No summary available",
        "llm_suggested_angle": sanitize_field(llm_suggested_angle)
        or "No suggested angle available",
        "signals": format_signals(signals),
        "score": score or 0,
    }
    return client_module.invoke_structured(
        function_name="review_lead",
        prompt=LEAD_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_lead_review_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def review_lead(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    score: float | None,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    result = review_lead_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        llm_summary=llm_summary,
        llm_suggested_angle=llm_suggested_angle,
        signals=signals,
        score=score,
        role=role,
    )
    if result.parsed is None:
        return _lead_review_fallback().model_dump()
    return result.parsed.model_dump()
