from __future__ import annotations

import json

from app.llm.contracts import (
    CommercialBriefResult,
    CommercialBriefReviewResult,
    DossierResult,
)
from app.llm.invocations.support import get_client_module
from app.llm.prompt_registry import (
    COMMERCIAL_BRIEF_PROMPT,
    COMMERCIAL_BRIEF_REVIEW_PROMPT,
    DOSSIER_PROMPT,
)
from app.llm.roles import LLMRole
from app.llm.sanitizer import sanitize_field


def _dossier_fallback(
    business_name: str,
    city: str | None,
) -> DossierResult:
    return DossierResult(
        business_description=(
            f"{business_name} - negocio en {city or 'ubicacion desconocida'}"
        ),
        digital_maturity="unknown",
        key_findings=[],
        improvement_opportunities=[],
        overall_assessment="Analisis no disponible.",
    )


def generate_dossier_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    score: float | None,
    signals: str | None,
    html_metadata: str | None,
    website_confidence: str | None,
    instagram_confidence: str | None,
    whatsapp_detected: bool | None,
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
        "score": score or 0,
        "signals": sanitize_field(signals) or "None",
        "html_metadata": sanitize_field(html_metadata) or "None",
        "website_confidence": website_confidence or "Unknown",
        "instagram_confidence": instagram_confidence or "Unknown",
        "whatsapp_detected": "Si" if whatsapp_detected else "No",
    }
    return client_module.invoke_structured(
        function_name="generate_dossier",
        prompt=DOSSIER_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _dossier_fallback(business_name, city),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def generate_dossier(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    score: float | None,
    signals: str | None,
    html_metadata: str | None,
    website_confidence: str | None,
    instagram_confidence: str | None,
    whatsapp_detected: bool | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> dict:
    result = generate_dossier_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        score=score,
        signals=signals,
        html_metadata=html_metadata,
        website_confidence=website_confidence,
        instagram_confidence=instagram_confidence,
        whatsapp_detected=whatsapp_detected,
        role=role,
    )
    if result.parsed is None:
        return _dossier_fallback(business_name, city).model_dump()
    return result.parsed.model_dump()


def _commercial_brief_fallback() -> CommercialBriefResult:
    return CommercialBriefResult(
        opportunity_score=50,
        estimated_scope="landing",
        recommended_contact_method="manual_review",
        should_call="maybe",
        call_reason="No se pudo generar el análisis automáticamente",
        why_this_lead_matters="Pendiente de revisión manual",
        main_business_signals=[],
        main_digital_gaps=[],
        recommended_angle="Requiere revisión manual",
        demo_recommended=False,
    )


def generate_commercial_brief_structured(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    score: float | None,
    llm_summary: str | None,
    signals: list[str],
    research_data: dict,
    pricing_matrix: dict,
    role: LLMRole = LLMRole.EXECUTOR,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Desconocida",
        "city": sanitize_field(city) or "Desconocida",
        "website_url": sanitize_field(website_url) or "Sin website",
        "instagram_url": sanitize_field(instagram_url) or "Sin Instagram",
        "score": score or 0,
        "llm_summary": sanitize_field(llm_summary) or "Sin resumen",
        "signals": ", ".join(signals) if signals else "Ninguna",
        "research_data": (
            json.dumps(research_data, ensure_ascii=False)
            if research_data
            else "Sin datos"
        ),
        "pricing_matrix": json.dumps(pricing_matrix, ensure_ascii=False),
    }
    return client_module.invoke_structured(
        function_name="generate_commercial_brief",
        prompt=COMMERCIAL_BRIEF_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_commercial_brief_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def generate_commercial_brief(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    score: float | None,
    llm_summary: str | None,
    signals: list[str],
    research_data: dict,
    pricing_matrix: dict,
    role: LLMRole = LLMRole.EXECUTOR,
) -> dict:
    result = generate_commercial_brief_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        website_url=website_url,
        instagram_url=instagram_url,
        score=score,
        llm_summary=llm_summary,
        signals=signals,
        research_data=research_data,
        pricing_matrix=pricing_matrix,
        role=role,
    )
    payload = (
        result.parsed.model_dump()
        if result.parsed is not None
        else _commercial_brief_fallback().model_dump()
    )
    payload["model"] = result.model
    payload["_is_fallback"] = result.fallback_used
    payload["_llm_status"] = result.status.value
    payload["_prompt_id"] = result.prompt_id
    payload["_prompt_version"] = result.prompt_version
    return payload


def _commercial_brief_review_fallback() -> CommercialBriefReviewResult:
    return CommercialBriefReviewResult(
        approved=False,
        feedback="Reviewer analysis unavailable.",
        suggested_changes="Review this brief manually before proceeding.",
    )


def review_commercial_brief_structured(
    *,
    opportunity_score: float | int | None,
    budget_tier: str | None,
    estimated_scope: str | None,
    recommended_contact_method: str | None,
    should_call: str | None,
    call_reason: str | None,
    why_this_lead_matters: str | None,
    main_business_signals: list[str] | None,
    main_digital_gaps: list[str] | None,
    recommended_angle: str | None,
    demo_recommended: bool | None,
    role: LLMRole | str = LLMRole.REVIEWER,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "opportunity_score": opportunity_score if opportunity_score is not None else "N/A",
        "budget_tier": budget_tier or "N/A",
        "estimated_scope": estimated_scope or "N/A",
        "recommended_contact_method": recommended_contact_method or "N/A",
        "should_call": should_call or "N/A",
        "call_reason": sanitize_field(call_reason) or "N/A",
        "why_this_lead_matters": sanitize_field(why_this_lead_matters) or "N/A",
        "main_business_signals": ", ".join(main_business_signals or []) or "N/A",
        "main_digital_gaps": ", ".join(main_digital_gaps or []) or "N/A",
        "recommended_angle": sanitize_field(recommended_angle) or "N/A",
        "demo_recommended": demo_recommended if demo_recommended is not None else "N/A",
    }
    return client_module.invoke_structured(
        function_name="review_commercial_brief",
        prompt=COMMERCIAL_BRIEF_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_commercial_brief_review_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def review_commercial_brief(
    *,
    opportunity_score: float | int | None,
    budget_tier: str | None,
    estimated_scope: str | None,
    recommended_contact_method: str | None,
    should_call: str | None,
    call_reason: str | None,
    why_this_lead_matters: str | None,
    main_business_signals: list[str] | None,
    main_digital_gaps: list[str] | None,
    recommended_angle: str | None,
    demo_recommended: bool | None,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    result = review_commercial_brief_structured(
        opportunity_score=opportunity_score,
        budget_tier=budget_tier,
        estimated_scope=estimated_scope,
        recommended_contact_method=recommended_contact_method,
        should_call=should_call,
        call_reason=call_reason,
        why_this_lead_matters=why_this_lead_matters,
        main_business_signals=main_business_signals,
        main_digital_gaps=main_digital_gaps,
        recommended_angle=recommended_angle,
        demo_recommended=demo_recommended,
        role=role,
    )
    payload = (
        result.parsed.model_dump()
        if result.parsed is not None
        else _commercial_brief_review_fallback().model_dump()
    )
    payload["model"] = result.model
    payload["_is_fallback"] = result.fallback_used
    payload["_llm_status"] = result.status.value
    payload["_prompt_id"] = result.prompt_id
    payload["_prompt_version"] = result.prompt_version
    return payload
