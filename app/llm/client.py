"""Ollama LLM client that resolves the configured model by role.

Uses /api/chat with system/user message separation for prompt injection defense.
"""

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import structlog
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.llm.contracts import (
    BusinessSummaryResult,
    CommercialBriefResult,
    CommercialBriefReviewResult,
    DossierResult,
    InboundReplyReviewResult,
    LeadQualityResult,
    LeadReviewResult,
    OutreachDraftResult,
    ReplyClassificationResult,
    StructuredInvocationResult,
    TextInvocationResult,
)
from app.llm.invocation_metadata import (
    LLMInvocationMetadata,
    record_invocation,
)
from app.llm.prompt_registry import (
    BUSINESS_SUMMARY_PROMPT,
    COMMERCIAL_BRIEF_PROMPT,
    COMMERCIAL_BRIEF_REVIEW_PROMPT,
    DOSSIER_PROMPT,
    INBOUND_REPLY_CLASSIFICATION_PROMPT,
    INBOUND_REPLY_REVIEW_PROMPT,
    LEAD_QUALITY_PROMPT,
    LEAD_REVIEW_PROMPT,
    OUTREACH_DRAFT_PROMPT,
    PromptDefinition,
)
from app.llm.prompts import (
    GENERATE_REPLY_ASSISTANT_DRAFT_DATA,
    GENERATE_REPLY_ASSISTANT_DRAFT_SYSTEM,
    GENERATE_WHATSAPP_DRAFT_DATA,
    GENERATE_WHATSAPP_DRAFT_SYSTEM,
    REVIEW_OUTREACH_DRAFT_DATA,
    REVIEW_OUTREACH_DRAFT_SYSTEM,
    REVIEW_REPLY_ASSISTANT_DRAFT_DATA,
    REVIEW_REPLY_ASSISTANT_DRAFT_SYSTEM,
)
from app.llm.resolver import normalize_role, resolve_model_for_role
from app.llm.roles import LLMRole
from app.llm.sanitizer import sanitize_field
from app.llm.types import LLMInvocationStatus
from app.models.llm_invocation import LLMInvocation

logger = get_logger(__name__)


class LLMError(Exception):
    pass


class LLMParseError(LLMError):
    pass


@dataclass(slots=True)
class _ChatCompletion:
    text: str
    model: str
    latency_ms: int


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise LLMParseError(f"Could not extract JSON from LLM response: {text[:200]}")


def _resolve_role_model(role: LLMRole | str) -> tuple[LLMRole, str]:
    normalized_role = normalize_role(role)
    model = resolve_model_for_role(normalized_role)
    if not model:
        raise LLMError(f"No model configured for role {normalized_role.value}")
    return normalized_role, model


def _role_value(role: LLMRole | str) -> str:
    try:
        return normalize_role(role).value
    except ValueError:
        return str(role)


def _timeout_for_role(role: LLMRole | str) -> float:
    normalized_role = normalize_role(role)
    if normalized_role == LLMRole.REVIEWER:
        return float(settings.OLLAMA_REVIEWER_TIMEOUT)
    if normalized_role == LLMRole.AGENT:
        return float(settings.OLLAMA_AGENT_TIMEOUT)
    return float(settings.OLLAMA_TIMEOUT)


def _normalize_tags(tags: dict[str, object] | None) -> dict[str, str]:
    if not tags:
        return {}
    return {str(key): str(value) for key, value in tags.items() if value is not None}


def _context_value(context: dict[str, object], key: str) -> str | None:
    value = context.get(key)
    if value in (None, ""):
        return None
    return str(value)


def _persist_invocation(metadata: LLMInvocationMetadata) -> None:
    context = structlog.contextvars.get_contextvars()
    try:
        with SessionLocal() as db:
            db.add(
                LLMInvocation(
                    function_name=metadata.function_name,
                    prompt_id=metadata.prompt_id,
                    prompt_version=metadata.prompt_version,
                    role=metadata.role,
                    model=metadata.model,
                    status=metadata.status,
                    fallback_used=metadata.fallback_used,
                    degraded=metadata.degraded,
                    parse_valid=metadata.parse_valid,
                    latency_ms=metadata.latency_ms,
                    target_type=metadata.target_type,
                    target_id=metadata.target_id,
                    correlation_id=_context_value(context, "correlation_id"),
                    task_id=_context_value(context, "task_id"),
                    pipeline_run_id=_context_value(context, "pipeline_run_id"),
                    lead_id=_context_value(context, "lead_id"),
                    tags_json=metadata.tags or None,
                    error=metadata.error,
                )
            )
            db.commit()
    except Exception as exc:
        logger.warning(
            "llm_invocation_persist_failed",
            function_name=metadata.function_name,
            prompt_id=metadata.prompt_id,
            prompt_version=metadata.prompt_version,
            error=str(exc),
        )


def _record_public_invocation(
    function_name: str,
    role: LLMRole | str,
    *,
    fallback_used: bool,
    degraded: bool,
    prompt_id: str | None = None,
    prompt_version: str = "legacy",
    status: LLMInvocationStatus | None = None,
    parse_valid: bool | None = None,
    latency_ms: int | None = None,
    model: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
    persist: bool = False,
    error: str | None = None,
) -> None:
    role_value = _role_value(role)
    if model is None:
        try:
            _, model = _resolve_role_model(role)
        except Exception:
            model = None

    if status is None:
        if fallback_used:
            status = LLMInvocationStatus.FALLBACK
        elif degraded:
            status = LLMInvocationStatus.DEGRADED
        else:
            status = LLMInvocationStatus.SUCCEEDED
    if parse_valid is None:
        parse_valid = not fallback_used

    metadata = LLMInvocationMetadata(
        function_name=function_name,
        prompt_id=prompt_id or function_name,
        prompt_version=prompt_version,
        role=role_value,
        status=status,
        model=model,
        fallback_used=fallback_used,
        degraded=degraded,
        parse_valid=parse_valid,
        latency_ms=latency_ms,
        error=error,
        target_type=target_type,
        target_id=target_id,
        tags=_normalize_tags(tags),
    )

    record_invocation(metadata)
    if persist:
        _persist_invocation(metadata)

    if fallback_used or degraded:
        logger.warning(
            "llm_invocation_degraded",
            function_name=function_name,
            prompt_id=metadata.prompt_id,
            prompt_version=metadata.prompt_version,
            status=metadata.status,
            role=role_value,
            model=model,
            fallback_used=fallback_used,
            degraded=degraded,
            parse_valid=parse_valid,
            latency_ms=latency_ms,
            target_type=target_type,
            target_id=target_id,
            error=error,
        )
    else:
        logger.debug(
            "llm_invocation_completed",
            function_name=function_name,
            prompt_id=metadata.prompt_id,
            prompt_version=metadata.prompt_version,
            status=metadata.status,
            role=role_value,
            model=model,
            parse_valid=parse_valid,
            latency_ms=latency_ms,
            target_type=target_type,
            target_id=target_id,
        )


@retry(
    stop=stop_after_attempt(settings.OLLAMA_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _chat_completion(
    system_prompt: str,
    user_prompt: str,
    role: LLMRole | str = LLMRole.EXECUTOR,
    *,
    format_schema: dict | None = None,
) -> _ChatCompletion:
    normalized_role, model = _resolve_role_model(role)
    timeout_seconds = _timeout_for_role(normalized_role)
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 2048,
        },
    }
    if format_schema:
        payload["format"] = format_schema

    logger.debug(
        "ollama_request",
        role=normalized_role.value,
        model=model,
        system_len=len(system_prompt),
        user_len=len(user_prompt),
        timeout_seconds=timeout_seconds,
        structured_output=bool(format_schema),
    )

    started_at = time.perf_counter()
    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    data = resp.json()
    message = data.get("message", {})
    response_text = message.get("content", "")

    if not response_text.strip():
        raise LLMError("Empty response from Ollama")

    logger.debug(
        "ollama_response",
        role=normalized_role.value,
        model=model,
        response_len=len(response_text),
        latency_ms=latency_ms,
        structured_output=bool(format_schema),
    )
    return _ChatCompletion(text=response_text, model=model, latency_ms=latency_ms)


def _call_ollama_chat(
    system_prompt: str,
    user_prompt: str,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> str:
    """Call Ollama /api/chat with system/user message separation."""
    return _chat_completion(system_prompt, user_prompt, role=role).text


def invoke_text(
    *,
    function_name: str,
    prompt_id: str,
    prompt_version: str,
    system_prompt: str,
    user_prompt: str,
    role: LLMRole | str = LLMRole.EXECUTOR,
    fallback_text: str | Callable[[], str] | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
    persist: bool = True,
) -> TextInvocationResult:
    normalized_role, model = _resolve_role_model(role)

    try:
        completion = _chat_completion(system_prompt, user_prompt, role=role)
        result = TextInvocationResult(
            status=LLMInvocationStatus.SUCCEEDED,
            role=normalized_role.value,
            model=completion.model,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            latency_ms=completion.latency_ms,
            fallback_used=False,
            degraded=False,
            parse_valid=True,
            raw_text=completion.text,
            text=completion.text,
            target_type=target_type,
            target_id=target_id,
            tags=_normalize_tags(tags),
        )
    except Exception as exc:
        fallback_value = fallback_text() if callable(fallback_text) else fallback_text
        result = TextInvocationResult(
            status=LLMInvocationStatus.FALLBACK
            if fallback_value is not None
            else LLMInvocationStatus.FAILED,
            role=normalized_role.value,
            model=model,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            fallback_used=fallback_value is not None,
            degraded=fallback_value is not None,
            parse_valid=fallback_value is not None,
            text=fallback_value,
            error=str(exc),
            target_type=target_type,
            target_id=target_id,
            tags=_normalize_tags(tags),
        )

    _record_public_invocation(
        function_name,
        role,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        status=result.status,
        fallback_used=result.fallback_used,
        degraded=result.degraded,
        parse_valid=result.parse_valid,
        latency_ms=result.latency_ms,
        model=result.model,
        target_type=result.target_type,
        target_id=result.target_id,
        tags=result.tags,
        persist=persist,
        error=result.error,
    )
    return result


def invoke_structured[StructuredT: BaseModel](
    *,
    function_name: str,
    prompt: PromptDefinition[StructuredT],
    prompt_args: dict[str, object],
    role: LLMRole | str = LLMRole.EXECUTOR,
    fallback_factory: Callable[[], StructuredT] | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
    persist: bool = True,
) -> StructuredInvocationResult[StructuredT]:
    normalized_role, model = _resolve_role_model(role)
    prompt_tags = _normalize_tags(tags)
    user_prompt = prompt.render_user_prompt(**prompt_args)

    try:
        completion = _chat_completion(
            prompt.system_prompt,
            user_prompt,
            role=role,
            format_schema=prompt.response_model.model_json_schema(),
        )
    except Exception as exc:
        parsed = fallback_factory() if fallback_factory else None
        result = StructuredInvocationResult[StructuredT](
            status=LLMInvocationStatus.FALLBACK
            if parsed is not None
            else LLMInvocationStatus.FAILED,
            role=normalized_role.value,
            model=model,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            fallback_used=parsed is not None,
            degraded=parsed is not None,
            parse_valid=False,
            parsed=parsed,
            error=str(exc),
            target_type=target_type,
            target_id=target_id,
            tags=prompt_tags,
        )
    else:
        parse_error: str | None = None
        try:
            parsed = prompt.response_model.model_validate_json(completion.text)
            result = StructuredInvocationResult[StructuredT](
                status=LLMInvocationStatus.SUCCEEDED,
                role=normalized_role.value,
                model=completion.model,
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.prompt_version,
                latency_ms=completion.latency_ms,
                fallback_used=False,
                degraded=False,
                parse_valid=True,
                raw_text=completion.text,
                parsed=parsed,
                target_type=target_type,
                target_id=target_id,
                tags=prompt_tags,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            parse_error = str(exc)
            try:
                parsed = prompt.response_model.model_validate(
                    _extract_json(completion.text)
                )
                result = StructuredInvocationResult[StructuredT](
                    status=LLMInvocationStatus.DEGRADED,
                    role=normalized_role.value,
                    model=completion.model,
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.prompt_version,
                    latency_ms=completion.latency_ms,
                    fallback_used=False,
                    degraded=True,
                    parse_valid=True,
                    raw_text=completion.text,
                    parsed=parsed,
                    error=parse_error,
                    target_type=target_type,
                    target_id=target_id,
                    tags=prompt_tags,
                )
            except Exception as recovery_exc:
                parsed = fallback_factory() if fallback_factory else None
                status = (
                    LLMInvocationStatus.FALLBACK
                    if parsed is not None
                    else LLMInvocationStatus.PARSE_FAILED
                )
                error = (
                    f"{parse_error}; recovery_error={recovery_exc}"
                    if parse_error
                    else str(recovery_exc)
                )
                result = StructuredInvocationResult[StructuredT](
                    status=status,
                    role=normalized_role.value,
                    model=completion.model,
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.prompt_version,
                    latency_ms=completion.latency_ms,
                    fallback_used=parsed is not None,
                    degraded=True,
                    parse_valid=False,
                    raw_text=completion.text,
                    parsed=parsed,
                    error=error,
                    target_type=target_type,
                    target_id=target_id,
                    tags=prompt_tags,
                )

    _record_public_invocation(
        function_name,
        role,
        prompt_id=prompt.prompt_id,
        prompt_version=prompt.prompt_version,
        status=result.status,
        fallback_used=result.fallback_used,
        degraded=result.degraded,
        parse_valid=result.parse_valid,
        latency_ms=result.latency_ms,
        model=result.model,
        target_type=result.target_type,
        target_id=result.target_id,
        tags=result.tags,
        persist=persist,
        error=result.error,
    )
    return result


def _format_signals(signals: list) -> str:
    """Format lead signals for prompt context."""
    if not signals:
        return "None detected"
    return ", ".join(f"{s.signal_type.value}: {s.detail or 'N/A'}" for s in signals)


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
) -> StructuredInvocationResult[BusinessSummaryResult]:
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "signals": _format_signals(signals),
    }
    return invoke_structured(
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
    """Generate a business summary using the local LLM."""
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
        return _business_summary_fallback(
            business_name,
            industry,
            city,
        ).summary
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
) -> StructuredInvocationResult[LeadQualityResult]:
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "signals": _format_signals(signals),
        "score": score or 0,
    }
    return invoke_structured(
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
    """Evaluate lead quality using the local LLM. Returns dict with quality, reasoning, suggested_angle."""
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
) -> dict:
    """Generate an outreach email draft. Returns dict with subject and body."""
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
    )
    if result.parsed is None:
        return _outreach_draft_fallback(business_name).model_dump()
    return result.parsed.model_dump()


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
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
) -> StructuredInvocationResult[OutreachDraftResult]:
    bc = brand_context or {}
    user_prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "llm_summary": sanitize_field(llm_summary) or "No summary available",
        "llm_suggested_angle": sanitize_field(llm_suggested_angle)
        or "Web development services",
        "signals": _format_signals(signals),
        "brand_name": bc.get("brand_name") or "No especificado",
        "signature_name": bc.get("signature_name") or "No especificado",
        "signature_role": bc.get("signature_role") or "No especificado",
        "signature_company": bc.get("signature_company") or "No especificado",
        "brand_website_url": bc.get("website_url")
        or "No proporcionado — NO inventar URLs",
        "portfolio_url": bc.get("portfolio_url")
        or "No proporcionado — NO inventar URLs",
        "calendar_url": bc.get("calendar_url")
        or "No proporcionado — NO inventar URLs",
        "signature_cta": bc.get("signature_cta") or "No especificado",
        "default_outreach_tone": bc.get("default_outreach_tone")
        or "profesional",
        "default_closing_line": bc.get("default_closing_line")
        or "No especificado",
        "signature_include_portfolio": bc.get(
            "signature_include_portfolio", True
        )
        and bool(bc.get("portfolio_url")),
        "sender_is_solo": bc.get("signature_is_solo", False),
    }
    return invoke_structured(
        function_name="generate_outreach_draft",
        prompt=OUTREACH_DRAFT_PROMPT,
        prompt_args=user_prompt_args,
        role=role,
        fallback_factory=lambda: _outreach_draft_fallback(business_name),
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
    """Run a reviewer pass on a lead. Returns verdict, confidence, reasoning, recommended_action, watchouts."""
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
) -> StructuredInvocationResult[LeadReviewResult]:
    prompt_args = {
        "business_name": sanitize_field(business_name),
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "website_url": sanitize_field(website_url) or "None",
        "instagram_url": sanitize_field(instagram_url) or "None",
        "llm_summary": sanitize_field(llm_summary) or "No summary available",
        "llm_suggested_angle": sanitize_field(llm_suggested_angle)
        or "No suggested angle available",
        "signals": _format_signals(signals),
        "score": score or 0,
    }
    return invoke_structured(
        function_name="review_lead",
        prompt=LEAD_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_lead_review_fallback,
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
    """Run a reviewer pass on an outreach draft."""
    user_prompt = REVIEW_OUTREACH_DRAFT_DATA.format(
        business_name=sanitize_field(business_name),
        industry=sanitize_field(industry) or "Unknown",
        city=sanitize_field(city) or "Unknown",
        website_url=sanitize_field(website_url) or "None",
        instagram_url=sanitize_field(instagram_url) or "None",
        llm_summary=sanitize_field(llm_summary) or "No summary available",
        llm_suggested_angle=sanitize_field(llm_suggested_angle)
        or "No suggested angle available",
        signals=_format_signals(signals),
        subject=sanitize_field(subject),
        body=sanitize_field(body),
    )

    fallback = {
        "verdict": "revise",
        "confidence": "low",
        "reasoning": "Reviewer analysis unavailable.",
        "strengths": [],
        "concerns": ["Reviewer output unavailable"],
        "suggested_changes": ["Review this draft manually before sending."],
        "revised_subject": None,
        "revised_body": None,
    }

    try:
        raw = _call_ollama_chat(REVIEW_OUTREACH_DRAFT_SYSTEM, user_prompt, role=role)
        data = _extract_json(raw)
        result = {
            "verdict": data.get("verdict", "revise"),
            "confidence": data.get("confidence", "medium"),
            "reasoning": data.get("reasoning", "No reasoning provided"),
            "strengths": data.get("strengths", []) or [],
            "concerns": data.get("concerns", []) or [],
            "suggested_changes": data.get("suggested_changes", []) or [],
            "revised_subject": data.get("revised_subject"),
            "revised_body": data.get("revised_body"),
        }
        _record_public_invocation(
            "review_outreach_draft",
            role,
            fallback_used=False,
            degraded=False,
        )
        return result
    except Exception as e:
        logger.error("llm_review_draft_failed", role=_role_value(role), error=str(e))
        _record_public_invocation(
            "review_outreach_draft",
            role,
            fallback_used=True,
            degraded=True,
            error=str(e),
        )
        return fallback


def classify_inbound_reply(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> dict:
    """Classify an inbound reply with the executor model."""
    result = classify_inbound_reply_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        lead_email=lead_email,
        outbound_subject=outbound_subject,
        outbound_message_id=outbound_message_id,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        role=role,
    )
    if result.parsed is None:
        raise LLMError(result.error or "Inbound reply classification failed")
    return result.parsed.model_dump()


def classify_inbound_reply_structured(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
) -> StructuredInvocationResult[ReplyClassificationResult]:
    prompt_args = {
        "business_name": sanitize_field(business_name) or "Unknown",
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "lead_email": sanitize_field(lead_email) or "Unknown",
        "outbound_subject": sanitize_field(outbound_subject) or "Unknown",
        "outbound_message_id": outbound_message_id or "Unknown",
        "from_email": sanitize_field(from_email) or "Unknown",
        "to_email": sanitize_field(to_email) or "Unknown",
        "subject": sanitize_field(subject) or "No subject",
        "body_text": sanitize_field(body_text) or "No body text available",
    }
    return invoke_structured(
        function_name="classify_inbound_reply",
        prompt=INBOUND_REPLY_CLASSIFICATION_PROMPT,
        prompt_args=prompt_args,
        role=role,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def review_inbound_reply(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    """Run a reviewer pass on an inbound reply."""
    result = review_inbound_reply_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        lead_email=lead_email,
        outbound_subject=outbound_subject,
        outbound_message_id=outbound_message_id,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        classification_label=classification_label,
        classification_summary=classification_summary,
        next_action_suggestion=next_action_suggestion,
        should_escalate_reviewer=should_escalate_reviewer,
        role=role,
    )
    if result.parsed is None:
        return _review_inbound_reply_fallback().model_dump()
    return result.parsed.model_dump()


def _review_inbound_reply_fallback() -> InboundReplyReviewResult:
    return InboundReplyReviewResult(
        verdict="consider_reply",
        confidence="low",
        reasoning="Reviewer analysis unavailable.",
        recommended_action="Review this reply manually before responding.",
        suggested_response_angle=None,
        watchouts=["Reviewer output unavailable"],
    )


def review_inbound_reply_structured(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    role: LLMRole | str = LLMRole.REVIEWER,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
) -> StructuredInvocationResult[InboundReplyReviewResult]:
    prompt_args = {
        "business_name": sanitize_field(business_name) or "Unknown",
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "lead_email": sanitize_field(lead_email) or "Unknown",
        "outbound_subject": sanitize_field(outbound_subject) or "Unknown",
        "outbound_message_id": outbound_message_id or "Unknown",
        "from_email": sanitize_field(from_email) or "Unknown",
        "to_email": sanitize_field(to_email) or "Unknown",
        "subject": sanitize_field(subject) or "No subject",
        "body_text": sanitize_field(body_text) or "No body text available",
        "classification_label": classification_label or "None",
        "classification_summary": sanitize_field(classification_summary)
        or "No executor summary available",
        "next_action_suggestion": sanitize_field(next_action_suggestion)
        or "No executor suggestion available",
        "should_escalate_reviewer": "true"
        if should_escalate_reviewer
        else "false",
    }
    return invoke_structured(
        function_name="review_inbound_reply",
        prompt=INBOUND_REPLY_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_review_inbound_reply_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def generate_reply_assistant_draft(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    outbound_subject: str | None,
    outbound_body: str | None,
    thread_context: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
    brand_context: dict | None = None,
) -> dict:
    """Generate a grounded response draft for a real inbound reply."""
    bc = brand_context or {}
    user_prompt = GENERATE_REPLY_ASSISTANT_DRAFT_DATA.format(
        business_name=sanitize_field(business_name) or "Unknown",
        industry=sanitize_field(industry) or "Unknown",
        city=sanitize_field(city) or "Unknown",
        lead_email=sanitize_field(lead_email) or "Unknown",
        classification_label=classification_label or "Unknown",
        classification_summary=sanitize_field(classification_summary)
        or "No classification summary available",
        next_action_suggestion=sanitize_field(next_action_suggestion)
        or "No next action suggestion available",
        should_escalate_reviewer="true"
        if should_escalate_reviewer
        else "false",
        outbound_subject=sanitize_field(outbound_subject) or "Unknown",
        outbound_body=sanitize_field(outbound_body) or "Unknown",
        thread_context=sanitize_field(thread_context)
        or "No previous thread context available",
        from_email=sanitize_field(from_email) or "Unknown",
        to_email=sanitize_field(to_email) or "Unknown",
        subject=sanitize_field(subject) or "No subject",
        body_text=sanitize_field(body_text)
        or "No body text available",
        brand_name=bc.get("brand_name") or "No especificado",
        signature_name=bc.get("signature_name") or "No especificado",
        signature_role=bc.get("signature_role") or "No especificado",
        signature_company=bc.get("signature_company")
        or "No especificado",
        brand_website_url=bc.get("website_url")
        or "No proporcionado — NO inventar URLs",
        signature_cta=bc.get("signature_cta") or "No especificado",
        default_reply_tone=bc.get("default_reply_tone")
        or "profesional",
        default_closing_line=bc.get("default_closing_line")
        or "No especificado",
        sender_is_solo=bc.get("signature_is_solo", False),
    )

    fallback = {
        "subject": subject or "Re: Consulta",
        "body": "Gracias por tu mensaje. Quedo atento para seguir la conversación.",
        "summary": "Draft de respuesta generado con fallback por indisponibilidad del LLM.",
        "suggested_tone": "professional",
        "should_escalate_reviewer": True,
    }

    try:
        raw = _call_ollama_chat(GENERATE_REPLY_ASSISTANT_DRAFT_SYSTEM, user_prompt, role=role)
        data = _extract_json(raw)
        subject_value = data.get("subject")
        body_value = data.get("body")
        if not subject_value or not body_value:
            raise LLMParseError("Missing subject or body in reply assistant response")
        result = {
            "subject": str(subject_value).strip(),
            "body": str(body_value).strip(),
            "summary": str(data.get("summary", "")).strip() or None,
            "suggested_tone": str(data.get("suggested_tone", "")).strip() or None,
            "should_escalate_reviewer": bool(data.get("should_escalate_reviewer")),
        }
        _record_public_invocation(
            "generate_reply_assistant_draft",
            role,
            fallback_used=False,
            degraded=False,
        )
        return result
    except Exception as e:
        logger.error("llm_reply_assistant_failed", role=_role_value(role), error=str(e))
        _record_public_invocation(
            "generate_reply_assistant_draft",
            role,
            fallback_used=True,
            degraded=True,
            error=str(e),
        )
        return fallback


def review_reply_assistant_draft(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    reply_should_escalate_reviewer: bool,
    outbound_subject: str | None,
    outbound_body: str | None,
    thread_context: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    draft_subject: str,
    draft_body: str,
    draft_summary: str | None,
    suggested_tone: str | None,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    """Review an existing assisted reply draft without regenerating it."""
    user_prompt = REVIEW_REPLY_ASSISTANT_DRAFT_DATA.format(
        business_name=sanitize_field(business_name) or "Unknown",
        industry=sanitize_field(industry) or "Unknown",
        city=sanitize_field(city) or "Unknown",
        lead_email=sanitize_field(lead_email) or "Unknown",
        classification_label=classification_label or "Unknown",
        classification_summary=sanitize_field(classification_summary)
        or "No classification summary available",
        next_action_suggestion=sanitize_field(next_action_suggestion)
        or "No next action suggestion available",
        reply_should_escalate_reviewer="true"
        if reply_should_escalate_reviewer
        else "false",
        outbound_subject=sanitize_field(outbound_subject) or "Unknown",
        outbound_body=sanitize_field(outbound_body) or "Unknown",
        thread_context=sanitize_field(thread_context)
        or "No previous thread context available",
        from_email=sanitize_field(from_email) or "Unknown",
        to_email=sanitize_field(to_email) or "Unknown",
        subject=sanitize_field(subject) or "No subject",
        body_text=sanitize_field(body_text)
        or "No body text available",
        draft_subject=sanitize_field(draft_subject),
        draft_body=sanitize_field(draft_body),
        draft_summary=sanitize_field(draft_summary)
        or "No draft summary available",
        suggested_tone=suggested_tone or "Unknown",
    )

    fallback = {
        "summary": "Reviewer analysis unavailable.",
        "feedback": "No se pudo revisar el draft de forma automática. Conviene revisarlo manualmente.",
        "suggested_edits": ["Revisar manualmente antes de usar este draft."],
        "recommended_action": "edit_before_sending",
        "should_use_as_is": False,
        "should_edit": True,
        "should_escalate": True,
    }

    try:
        raw = _call_ollama_chat(REVIEW_REPLY_ASSISTANT_DRAFT_SYSTEM, user_prompt, role=role)
        data = _extract_json(raw)
        result = {
            "summary": str(data.get("summary", "")).strip() or fallback["summary"],
            "feedback": str(data.get("feedback", "")).strip() or fallback["feedback"],
            "suggested_edits": [str(item).strip() for item in (data.get("suggested_edits", []) or []) if str(item).strip()],
            "recommended_action": str(data.get("recommended_action", "")).strip() or fallback["recommended_action"],
            "should_use_as_is": bool(data.get("should_use_as_is")),
            "should_edit": bool(data.get("should_edit")),
            "should_escalate": bool(data.get("should_escalate")),
        }
        _record_public_invocation(
            "review_reply_assistant_draft",
            role,
            fallback_used=False,
            degraded=False,
        )
        return result
    except Exception as e:
        logger.error("llm_review_reply_assistant_failed", role=_role_value(role), error=str(e))
        _record_public_invocation(
            "review_reply_assistant_draft",
            role,
            fallback_used=True,
            degraded=True,
            error=str(e),
        )
        return fallback


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
    """Generate a WhatsApp outreach message. Returns dict with body."""
    user_prompt = GENERATE_WHATSAPP_DRAFT_DATA.format(
        business_name=sanitize_field(business_name),
        industry=sanitize_field(industry) or "Unknown",
        city=sanitize_field(city) or "Unknown",
        website_url=sanitize_field(website_url) or "None",
        instagram_url=sanitize_field(instagram_url) or "None",
        llm_summary=sanitize_field(llm_summary) or "No summary available",
        llm_suggested_angle=sanitize_field(llm_suggested_angle)
        or "Web development services",
        signals=_format_signals(signals),
    )

    fallback = {
        "body": f"Hola! Vi que {business_name} podría mejorar su presencia digital. "
        "Te interesaría charlar sobre cómo puedo ayudarte? 🚀",
    }

    try:
        raw = _call_ollama_chat(
            GENERATE_WHATSAPP_DRAFT_SYSTEM, user_prompt, role=role,
        )
        data = _extract_json(raw)
        body = data.get("body")
        if not body:
            raise LLMParseError("Missing body in WhatsApp draft response")
        _record_public_invocation(
            "generate_whatsapp_draft",
            role,
            fallback_used=False,
            degraded=False,
        )
        return {"body": body}
    except Exception as e:
        logger.error("llm_whatsapp_draft_failed", role=_role_value(role), error=str(e))
        _record_public_invocation(
            "generate_whatsapp_draft",
            role,
            fallback_used=True,
            degraded=True,
            error=str(e),
        )
        return fallback


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
    """Generate a structured dossier for a lead using the LLM."""
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
) -> StructuredInvocationResult[DossierResult]:
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
    return invoke_structured(
        function_name="generate_dossier",
        prompt=DOSSIER_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _dossier_fallback(business_name, city),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


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
) -> StructuredInvocationResult[CommercialBriefResult]:
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
    return invoke_structured(
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
    """Generate a commercial brief for a lead."""
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
) -> StructuredInvocationResult[CommercialBriefReviewResult]:
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
    return invoke_structured(
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
