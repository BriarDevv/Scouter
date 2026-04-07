from __future__ import annotations

from app.llm.contracts import OutreachDraftResult, OutreachDraftReviewResult, WhatsAppDraftResult
from app.llm.invocations.support import format_signals, get_client_module
from app.llm.prompt_registry import (
    OUTREACH_DRAFT_PROMPT,
    OUTREACH_DRAFT_REVIEW_PROMPT,
    WHATSAPP_DRAFT_PROMPT,
)
from app.llm.roles import LLMRole
from app.llm.sanitizer import sanitize_field


def _outreach_draft_fallback(business_name: str) -> OutreachDraftResult:
    return OutreachDraftResult(
        subject=f"Propuesta de desarrollo web para {business_name}",
        body=(
            f"Hola,\n\nSoy desarrollador web y noté que {business_name} podría "
            "beneficiarse de una mejora en su presencia digital.\n\n"
            "Me encantaría charlar sobre cómo puedo ayudarlos.\n\nSaludos."
        ),
    )


def generate_outreach_draft_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    role: LLMRole | str = LLMRole.EXECUTOR,
    brand_context: dict | None = None,
    pipeline_context: str = "",
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    bc = brand_context or {}
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "llm_summary": sanitize_field(llm_summary) or "No summary available",
        "llm_suggested_angle": sanitize_field(llm_suggested_angle) or "Web development services",
        "signals": format_signals(signals),
        "brand_name": bc.get("brand_name") or "No especificado",
        "signature_name": bc.get("signature_name") or "No especificado",
        "signature_role": bc.get("signature_role") or "No especificado",
        "signature_company": bc.get("signature_company") or "No especificado",
        "brand_website_url": bc.get("website_url") or "No proporcionado — NO inventar URLs",
        "portfolio_url": bc.get("portfolio_url") or "No proporcionado — NO inventar URLs",
        "calendar_url": bc.get("calendar_url") or "No proporcionado — NO inventar URLs",
        "signature_cta": bc.get("signature_cta") or "No especificado",
        "default_outreach_tone": bc.get("default_outreach_tone") or "profesional",
        "default_closing_line": bc.get("default_closing_line") or "No especificado",
        "signature_include_portfolio": bc.get("signature_include_portfolio", True)
        and bool(bc.get("portfolio_url")),
        "sender_is_solo": bc.get("signature_is_solo", False),
        "pipeline_context": pipeline_context or "No pipeline context available.",
    }
    return client_module.invoke_structured(
        function_name="generate_outreach_draft",
        prompt=OUTREACH_DRAFT_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _outreach_draft_fallback(business_name),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def generate_outreach_draft(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    role: LLMRole | str = LLMRole.EXECUTOR,
    brand_context: dict | None = None,
    pipeline_context: str = "",
) -> dict:
    result = generate_outreach_draft_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        llm_summary=llm_summary,
        llm_suggested_angle=llm_suggested_angle,
        signals=signals,
        role=role,
        brand_context=brand_context,
        pipeline_context=pipeline_context,
    )
    if result.parsed is None:
        return _outreach_draft_fallback(business_name).model_dump()
    return result.parsed.model_dump()


def _review_outreach_draft_fallback() -> OutreachDraftReviewResult:
    return OutreachDraftReviewResult(
        verdict="revise",
        confidence="low",
        reasoning="Reviewer analysis unavailable.",
        strengths=[],
        concerns=["Reviewer output unavailable"],
        suggested_changes=["Review this draft manually before sending."],
        revised_subject=None,
        revised_body=None,
    )


def review_outreach_draft_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    subject: str,
    body: str,
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
        "subject": sanitize_field(subject),
        "body": sanitize_field(body),
    }
    return client_module.invoke_structured(
        function_name="review_outreach_draft",
        prompt=OUTREACH_DRAFT_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_review_outreach_draft_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def review_outreach_draft(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    subject: str,
    body: str,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    result = review_outreach_draft_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        llm_summary=llm_summary,
        llm_suggested_angle=llm_suggested_angle,
        signals=signals,
        subject=subject,
        body=body,
        role=role,
    )
    if result.parsed is None:
        return _review_outreach_draft_fallback().model_dump()
    return result.parsed.model_dump()


def _whatsapp_draft_fallback(business_name: str) -> WhatsAppDraftResult:
    return WhatsAppDraftResult(
        body=(
            f"Hola! Vi que {business_name} podría mejorar su presencia digital. "
            "Te interesaría charlar sobre cómo puedo ayudarte? 🚀"
        )
    )


def generate_whatsapp_draft_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
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
        "llm_summary": sanitize_field(llm_summary) or "No summary available",
        "llm_suggested_angle": sanitize_field(llm_suggested_angle) or "Web development services",
        "signals": format_signals(signals),
    }
    return client_module.invoke_structured(
        function_name="generate_whatsapp_draft",
        prompt=WHATSAPP_DRAFT_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _whatsapp_draft_fallback(business_name),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def generate_whatsapp_draft(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    llm_summary: str | None,
    llm_suggested_angle: str | None,
    signals: list,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> dict:
    result = generate_whatsapp_draft_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        llm_summary=llm_summary,
        llm_suggested_angle=llm_suggested_angle,
        signals=signals,
        role=role,
    )
    if result.parsed is None:
        return _whatsapp_draft_fallback(business_name).model_dump()
    return result.parsed.model_dump()
