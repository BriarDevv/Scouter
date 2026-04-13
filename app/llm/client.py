"""Ollama LLM client that resolves the configured model by role.

Uses /api/chat with system/user message separation for prompt injection defense.
"""

import json
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

import httpx
import structlog
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.llm.contracts import StructuredInvocationResult, TextInvocationResult
from app.llm.invocation_metadata import LLMInvocationMetadata, record_invocation
from app.llm.prompt_registry import PromptDefinition
from app.llm.resolver import normalize_role, resolve_model_for_role
from app.llm.roles import LLMRole
from app.llm.types import LLMInvocationStatus
from app.models.llm_invocation import LLMInvocation

__all__ = [
    "LLMError",
    "LLMParseError",
    "PromptDefinition",
    "invoke_structured",
    "invoke_text",
]

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
        result: dict = json.loads(text)
        return result
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            return result
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            return result
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


def _normalize_tags(tags: Mapping[str, object] | None) -> dict[str, str]:
    if not tags:
        return {}
    return {str(key): str(value) for key, value in tags.items() if value is not None}


def _context_value(context: dict[str, object], key: str) -> str | None:
    value = context.get(key)
    if value in (None, ""):
        return None
    return str(value)


def _persist_invocation(metadata: LLMInvocationMetadata, db: "Session | None" = None) -> None:
    from sqlalchemy.orm import Session as _Session  # local to avoid circular at module level

    context = structlog.contextvars.get_contextvars()

    def _do_add(session: _Session) -> None:
        session.add(
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

    try:
        if db is not None:
            _do_add(db)
            db.flush()
        else:
            with SessionLocal() as new_db:
                _do_add(new_db)
                new_db.commit()
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
    tags: Mapping[str, object] | None = None,
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


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException | httpx.ConnectError | ConnectionError | OSError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


@retry(
    stop=stop_after_attempt(settings.OLLAMA_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(lambda e: _is_retryable(e)),
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
                parsed = prompt.response_model.model_validate(_extract_json(completion.text))
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
