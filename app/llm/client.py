"""Ollama LLM client that resolves the configured model by role."""

import json
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.prompts import (
    CLASSIFY_INBOUND_REPLY,
    EVALUATE_LEAD_QUALITY,
    GENERATE_REPLY_ASSISTANT_DRAFT,
    GENERATE_OUTREACH_EMAIL,
    REVIEW_REPLY_ASSISTANT_DRAFT,
    REVIEW_INBOUND_REPLY,
    REVIEW_LEAD,
    REVIEW_OUTREACH_DRAFT,
    SUMMARIZE_BUSINESS,
)
from app.llm.resolver import normalize_role, resolve_model_for_role
from app.llm.roles import LLMRole

logger = get_logger(__name__)


class LLMError(Exception):
    pass


class LLMParseError(LLMError):
    pass


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
    return float(settings.OLLAMA_TIMEOUT)


@retry(
    stop=stop_after_attempt(settings.OLLAMA_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _call_ollama(prompt: str, role: LLMRole | str = LLMRole.EXECUTOR) -> str:
    """Call Ollama API with the configured model for a given role."""
    normalized_role, model = _resolve_role_model(role)
    timeout_seconds = _timeout_for_role(normalized_role)
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        },
    }

    logger.debug(
        "ollama_request",
        role=normalized_role.value,
        model=model,
        prompt_len=len(prompt),
        timeout_seconds=timeout_seconds,
    )

    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    response_text = data.get("response", "")

    # Fallback: some models (Qwen 3+) put content in "thinking" field
    if not response_text.strip():
        response_text = data.get("thinking", "")

    if not response_text.strip():
        raise LLMError("Empty response from Ollama")

    logger.debug(
        "ollama_response",
        role=normalized_role.value,
        model=model,
        response_len=len(response_text),
    )
    return response_text


def _format_signals(signals: list) -> str:
    """Format lead signals for prompt injection."""
    if not signals:
        return "None detected"
    return ", ".join(f"{s.signal_type.value}: {s.detail or 'N/A'}" for s in signals)


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
    prompt = SUMMARIZE_BUSINESS.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        signals=_format_signals(signals),
    )

    try:
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        return data.get("summary", raw)
    except Exception as e:
        logger.error("llm_summarize_failed", role=_role_value(role), error=str(e))
        return f"[LLM unavailable] {business_name} - {industry or 'Unknown industry'} in {city or 'Unknown location'}"


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
    prompt = EVALUATE_LEAD_QUALITY.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        signals=_format_signals(signals),
        score=score or 0,
    )

    fallback = {
        "quality": "unknown",
        "reasoning": "LLM analysis unavailable",
        "suggested_angle": "General web development services",
    }

    try:
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        return {
            "quality": data.get("quality", "unknown"),
            "reasoning": data.get("reasoning", "No reasoning provided"),
            "suggested_angle": data.get("suggested_angle", "General web development services"),
        }
    except Exception as e:
        logger.error("llm_evaluate_failed", role=_role_value(role), error=str(e))
        return fallback


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
    bc = brand_context or {}
    prompt = GENERATE_OUTREACH_EMAIL.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        llm_summary=llm_summary or "No summary available",
        llm_suggested_angle=llm_suggested_angle or "Web development services",
        signals=_format_signals(signals),
        brand_name=bc.get("brand_name") or "No especificado",
        signature_name=bc.get("signature_name") or "No especificado",
        signature_role=bc.get("signature_role") or "No especificado",
        portfolio_url=bc.get("portfolio_url") or "No especificado",
        signature_cta=bc.get("signature_cta") or "No especificado",
        default_outreach_tone=bc.get("default_outreach_tone") or "profesional",
        default_closing_line=bc.get("default_closing_line") or "No especificado",
        signature_include_portfolio=bc.get("signature_include_portfolio", True),
    )

    fallback = {
        "subject": f"Propuesta de desarrollo web para {business_name}",
        "body": f"Hola,\n\nSoy desarrollador web y noté que {business_name} podría beneficiarse de una mejora en su presencia digital.\n\nMe encantaría charlar sobre cómo puedo ayudarlos.\n\nSaludos.",
    }

    try:
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        subject = data.get("subject")
        body = data.get("body")
        if not subject or not body:
            raise LLMParseError("Missing subject or body in LLM response")
        return {"subject": subject, "body": body}
    except Exception as e:
        logger.error("llm_outreach_failed", role=_role_value(role), error=str(e))
        return fallback


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
    prompt = REVIEW_LEAD.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        llm_summary=llm_summary or "No summary available",
        llm_suggested_angle=llm_suggested_angle or "No suggested angle available",
        signals=_format_signals(signals),
        score=score or 0,
    )

    fallback = {
        "verdict": "worth_follow_up",
        "confidence": "low",
        "reasoning": "Reviewer analysis unavailable.",
        "recommended_action": "Review this lead manually before taking action.",
        "watchouts": ["Reviewer output unavailable"],
    }

    try:
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        return {
            "verdict": data.get("verdict", "worth_follow_up"),
            "confidence": data.get("confidence", "medium"),
            "reasoning": data.get("reasoning", "No reasoning provided"),
            "recommended_action": data.get("recommended_action", "Review manually"),
            "watchouts": data.get("watchouts", []) or [],
        }
    except Exception as e:
        logger.error("llm_review_lead_failed", role=_role_value(role), error=str(e))
        return fallback


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
    prompt = REVIEW_OUTREACH_DRAFT.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        llm_summary=llm_summary or "No summary available",
        llm_suggested_angle=llm_suggested_angle or "No suggested angle available",
        signals=_format_signals(signals),
        subject=subject,
        body=body,
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
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        return {
            "verdict": data.get("verdict", "revise"),
            "confidence": data.get("confidence", "medium"),
            "reasoning": data.get("reasoning", "No reasoning provided"),
            "strengths": data.get("strengths", []) or [],
            "concerns": data.get("concerns", []) or [],
            "suggested_changes": data.get("suggested_changes", []) or [],
            "revised_subject": data.get("revised_subject"),
            "revised_body": data.get("revised_body"),
        }
    except Exception as e:
        logger.error("llm_review_draft_failed", role=_role_value(role), error=str(e))
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
    prompt = CLASSIFY_INBOUND_REPLY.format(
        business_name=business_name or "Unknown",
        industry=industry or "Unknown",
        city=city or "Unknown",
        lead_email=lead_email or "Unknown",
        outbound_subject=outbound_subject or "Unknown",
        outbound_message_id=outbound_message_id or "Unknown",
        from_email=from_email or "Unknown",
        to_email=to_email or "Unknown",
        subject=subject or "No subject",
        body_text=body_text or "No body text available",
    )

    try:
        raw = _call_ollama(prompt, role=role)
        return _extract_json(raw)
    except Exception as e:
        logger.error("llm_classify_inbound_failed", role=_role_value(role), error=str(e))
        raise


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
    prompt = REVIEW_INBOUND_REPLY.format(
        business_name=business_name or "Unknown",
        industry=industry or "Unknown",
        city=city or "Unknown",
        lead_email=lead_email or "Unknown",
        outbound_subject=outbound_subject or "Unknown",
        outbound_message_id=outbound_message_id or "Unknown",
        from_email=from_email or "Unknown",
        to_email=to_email or "Unknown",
        subject=subject or "No subject",
        body_text=body_text or "No body text available",
        classification_label=classification_label or "None",
        classification_summary=classification_summary or "No executor summary available",
        next_action_suggestion=next_action_suggestion or "No executor suggestion available",
        should_escalate_reviewer="true" if should_escalate_reviewer else "false",
    )

    fallback = {
        "verdict": "consider_reply",
        "confidence": "low",
        "reasoning": "Reviewer analysis unavailable.",
        "recommended_action": "Review this reply manually before responding.",
        "suggested_response_angle": None,
        "watchouts": ["Reviewer output unavailable"],
    }

    try:
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        return {
            "verdict": data.get("verdict", "consider_reply"),
            "confidence": data.get("confidence", "medium"),
            "reasoning": data.get("reasoning", "No reasoning provided"),
            "recommended_action": data.get("recommended_action", "Review manually"),
            "suggested_response_angle": data.get("suggested_response_angle"),
            "watchouts": data.get("watchouts", []) or [],
        }
    except Exception as e:
        logger.error("llm_review_inbound_failed", role=_role_value(role), error=str(e))
        return fallback


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
    prompt = GENERATE_REPLY_ASSISTANT_DRAFT.format(
        business_name=business_name or "Unknown",
        industry=industry or "Unknown",
        city=city or "Unknown",
        lead_email=lead_email or "Unknown",
        classification_label=classification_label or "Unknown",
        classification_summary=classification_summary or "No classification summary available",
        next_action_suggestion=next_action_suggestion or "No next action suggestion available",
        should_escalate_reviewer="true" if should_escalate_reviewer else "false",
        outbound_subject=outbound_subject or "Unknown",
        outbound_body=outbound_body or "Unknown",
        thread_context=thread_context or "No previous thread context available",
        from_email=from_email or "Unknown",
        to_email=to_email or "Unknown",
        subject=subject or "No subject",
        body_text=body_text or "No body text available",
        brand_name=bc.get("brand_name") or "No especificado",
        signature_name=bc.get("signature_name") or "No especificado",
        signature_role=bc.get("signature_role") or "No especificado",
        signature_cta=bc.get("signature_cta") or "No especificado",
        default_reply_tone=bc.get("default_reply_tone") or "profesional",
        default_closing_line=bc.get("default_closing_line") or "No especificado",
    )

    fallback = {
        "subject": subject or "Re: Consulta",
        "body": "Gracias por tu mensaje. Quedo atento para seguir la conversación.",
        "summary": "Draft de respuesta generado con fallback por indisponibilidad del LLM.",
        "suggested_tone": "professional",
        "should_escalate_reviewer": True,
    }

    try:
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        subject_value = data.get("subject")
        body_value = data.get("body")
        if not subject_value or not body_value:
            raise LLMParseError("Missing subject or body in reply assistant response")
        return {
            "subject": str(subject_value).strip(),
            "body": str(body_value).strip(),
            "summary": str(data.get("summary", "")).strip() or None,
            "suggested_tone": str(data.get("suggested_tone", "")).strip() or None,
            "should_escalate_reviewer": bool(data.get("should_escalate_reviewer")),
        }
    except Exception as e:
        logger.error("llm_reply_assistant_failed", role=_role_value(role), error=str(e))
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
    prompt = REVIEW_REPLY_ASSISTANT_DRAFT.format(
        business_name=business_name or "Unknown",
        industry=industry or "Unknown",
        city=city or "Unknown",
        lead_email=lead_email or "Unknown",
        classification_label=classification_label or "Unknown",
        classification_summary=classification_summary or "No classification summary available",
        next_action_suggestion=next_action_suggestion or "No next action suggestion available",
        reply_should_escalate_reviewer="true" if reply_should_escalate_reviewer else "false",
        outbound_subject=outbound_subject or "Unknown",
        outbound_body=outbound_body or "Unknown",
        thread_context=thread_context or "No previous thread context available",
        from_email=from_email or "Unknown",
        to_email=to_email or "Unknown",
        subject=subject or "No subject",
        body_text=body_text or "No body text available",
        draft_subject=draft_subject,
        draft_body=draft_body,
        draft_summary=draft_summary or "No draft summary available",
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
        raw = _call_ollama(prompt, role=role)
        data = _extract_json(raw)
        return {
            "summary": str(data.get("summary", "")).strip() or fallback["summary"],
            "feedback": str(data.get("feedback", "")).strip() or fallback["feedback"],
            "suggested_edits": [str(item).strip() for item in (data.get("suggested_edits", []) or []) if str(item).strip()],
            "recommended_action": str(data.get("recommended_action", "")).strip() or fallback["recommended_action"],
            "should_use_as_is": bool(data.get("should_use_as_is")),
            "should_edit": bool(data.get("should_edit")),
            "should_escalate": bool(data.get("should_escalate")),
        }
    except Exception as e:
        logger.error("llm_review_reply_assistant_failed", role=_role_value(role), error=str(e))
        return fallback
