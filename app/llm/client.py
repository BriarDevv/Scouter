"""Ollama LLM client for Qwen 14B integration."""

import json
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.prompts import EVALUATE_LEAD_QUALITY, GENERATE_OUTREACH_EMAIL, SUMMARIZE_BUSINESS

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


@retry(
    stop=stop_after_attempt(settings.OLLAMA_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _call_ollama(prompt: str) -> str:
    """Call Ollama API with the configured model."""
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        },
    }

    logger.debug("ollama_request", model=settings.OLLAMA_MODEL, prompt_len=len(prompt))

    with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    response_text = data.get("response", "")

    # Fallback: some models (Qwen 3+) put content in "thinking" field
    if not response_text.strip():
        response_text = data.get("thinking", "")

    if not response_text.strip():
        raise LLMError("Empty response from Ollama")

    logger.debug("ollama_response", response_len=len(response_text))
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
        raw = _call_ollama(prompt)
        data = _extract_json(raw)
        return data.get("summary", raw)
    except Exception as e:
        logger.error("llm_summarize_failed", error=str(e))
        return f"[LLM unavailable] {business_name} - {industry or 'Unknown industry'} in {city or 'Unknown location'}"


def evaluate_lead_quality(
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    signals: list,
    score: float | None,
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
        raw = _call_ollama(prompt)
        data = _extract_json(raw)
        return {
            "quality": data.get("quality", "unknown"),
            "reasoning": data.get("reasoning", "No reasoning provided"),
            "suggested_angle": data.get("suggested_angle", "General web development services"),
        }
    except Exception as e:
        logger.error("llm_evaluate_failed", error=str(e))
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
) -> dict:
    """Generate an outreach email draft. Returns dict with subject and body."""
    prompt = GENERATE_OUTREACH_EMAIL.format(
        business_name=business_name,
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        llm_summary=llm_summary or "No summary available",
        llm_suggested_angle=llm_suggested_angle or "Web development services",
        signals=_format_signals(signals),
    )

    fallback = {
        "subject": f"Propuesta de desarrollo web para {business_name}",
        "body": f"Hola,\n\nSoy desarrollador web y noté que {business_name} podría beneficiarse de una mejora en su presencia digital.\n\nMe encantaría charlar sobre cómo puedo ayudarlos.\n\nSaludos.",
    }

    try:
        raw = _call_ollama(prompt)
        data = _extract_json(raw)
        subject = data.get("subject")
        body = data.get("body")
        if not subject or not body:
            raise LLMParseError("Missing subject or body in LLM response")
        return {"subject": subject, "body": body}
    except Exception as e:
        logger.error("llm_outreach_failed", error=str(e))
        return fallback
