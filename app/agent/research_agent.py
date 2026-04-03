"""Scout research agent — synchronous agent loop for deep lead investigation.

Scout uses qwen3.5:9b with Playwright tools to investigate a business's
digital presence. Unlike Mote (async streaming), Scout runs synchronously
inside a Celery worker and returns a structured result.

Architecture follows the Hermes 3 tool-calling format from hermes_format.py
but in a synchronous loop with a fixed toolset.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.agent.hermes_format import (
    contains_tool_call,
    format_tool_result,
    parse_tool_calls,
)
from app.agent.scout_prompts import SCOUT_SYSTEM_PROMPT, SCOUT_USER_PROMPT_TEMPLATE
from app.agent.scout_tools import SCOUT_TOOLS, build_scout_tools_schema
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole

logger = get_logger(__name__)

MAX_SCOUT_LOOPS = 10
SCOUT_TIMEOUT_SECONDS = 90


@dataclass
class ScoutResult:
    """Result of a Scout investigation."""

    findings: dict = field(default_factory=dict)
    pages_visited: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    duration_ms: int = 0
    loops_used: int = 0
    error: str | None = None


def _call_ollama_sync(
    model: str,
    messages: list[dict[str, str]],
    timeout: float = SCOUT_TIMEOUT_SECONDS,
) -> str:
    """Synchronous Ollama chat completion (non-streaming)."""
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 2048,
        },
    }
    resp = httpx.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")


def _execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a Scout tool and return its result."""
    tool_def = SCOUT_TOOLS.get(name)
    if not tool_def:
        return {"error": f"Unknown tool: {name}"}

    handler = tool_def["handler"]
    try:
        return handler(**arguments)
    except Exception as exc:
        logger.warning("scout_tool_error", tool=name, error=str(exc))
        return {"error": str(exc)}


def run_scout_investigation(
    *,
    business_name: str,
    industry: str | None,
    city: str | None,
    website_url: str | None,
    instagram_url: str | None,
    score: float | None,
    signals: str,
    analysis_context: str = "",
    max_loops: int = MAX_SCOUT_LOOPS,
    timeout_seconds: float = SCOUT_TIMEOUT_SECONDS,
) -> ScoutResult:
    """Run a Scout investigation on a lead.

    Synchronous agent loop: prompt → LLM → parse tool calls → execute →
    feed results back → repeat until finish_investigation or max loops.

    Returns ScoutResult with findings, pages visited, and full tool history.
    """
    start_time = time.monotonic()
    result = ScoutResult()

    # Resolve model
    model = resolve_model_for_role(LLMRole.EXECUTOR)
    if not model:
        result.error = "No model configured for EXECUTOR role"
        return result

    # Build system prompt with tools
    tools_schema = build_scout_tools_schema()
    system_prompt = (
        SCOUT_SYSTEM_PROMPT
        + "\n\n## Available Tools\n\n"
        + tools_schema
    )

    # Build initial user message
    user_message = SCOUT_USER_PROMPT_TEMPLATE.format(
        business_name=business_name or "Unknown",
        industry=industry or "Unknown",
        city=city or "Unknown",
        website_url=website_url or "None",
        instagram_url=instagram_url or "None",
        score=score or 0,
        signals=signals or "None",
        analysis_context=analysis_context or "No prior analysis",
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    investigation_complete = False

    for loop_idx in range(max_loops):
        # Check timeout
        elapsed = time.monotonic() - start_time
        if elapsed > timeout_seconds:
            logger.warning("scout_timeout", loops=loop_idx, elapsed_s=round(elapsed, 1))
            result.error = f"Timeout after {round(elapsed, 1)}s"
            break

        result.loops_used = loop_idx + 1

        # Call LLM
        try:
            remaining_timeout = max(10, timeout_seconds - elapsed)
            response_text = _call_ollama_sync(model, messages, timeout=remaining_timeout)
        except Exception as exc:
            logger.error("scout_llm_error", loop=loop_idx, error=str(exc))
            result.error = f"LLM error: {str(exc)}"
            break

        # Check for tool calls
        if not contains_tool_call(response_text):
            # No tool calls — model is done (or confused)
            logger.info("scout_no_tool_calls", loop=loop_idx)
            break

        # Parse and execute tool calls
        tool_calls = parse_tool_calls(response_text)
        if not tool_calls:
            break

        # Add assistant response to messages
        messages.append({"role": "assistant", "content": response_text})

        tool_results_text = ""
        for tc in tool_calls:
            tool_start = time.monotonic()
            tool_result = _execute_tool(tc.name, tc.arguments)
            tool_duration_ms = int((time.monotonic() - tool_start) * 1000)

            # Record for thread storage
            result.tool_calls.append({
                "name": tc.name,
                "arguments": tc.arguments,
                "result": _truncate_result(tool_result),
                "duration_ms": tool_duration_ms,
                "timestamp": time.time(),
            })

            # Track pages visited
            if tc.name == "browse_page" and "url" in tool_result:
                result.pages_visited.append({
                    "url": tool_result.get("url", tc.arguments.get("url", "")),
                    "title": tool_result.get("title"),
                    "status_code": tool_result.get("status_code"),
                })

            # Check if investigation is complete
            if tc.name == "finish_investigation":
                findings = tool_result.get("findings", {})
                if isinstance(findings, dict):
                    result.findings = findings
                else:
                    result.findings = {"raw": str(findings)}
                investigation_complete = True

            tool_results_text += format_tool_result(tc.name, tool_result) + "\n"

            logger.info(
                "scout_tool_executed",
                tool=tc.name,
                duration_ms=tool_duration_ms,
                loop=loop_idx,
            )

        # Append tool results as user message
        messages.append({"role": "user", "content": tool_results_text.strip()})

        if investigation_complete:
            break

    result.duration_ms = int((time.monotonic() - start_time) * 1000)

    if not result.findings and not result.error:
        # Agent didn't call finish_investigation — extract what we can
        result.findings = {
            "opportunity": "Investigation incomplete — agent did not produce final summary",
            "pages_visited_count": len(result.pages_visited),
        }

    logger.info(
        "scout_investigation_complete",
        business_name=business_name,
        loops=result.loops_used,
        duration_ms=result.duration_ms,
        pages_visited=len(result.pages_visited),
        tool_calls=len(result.tool_calls),
        has_findings=bool(result.findings),
        error=result.error,
    )

    return result


def _truncate_result(result: dict, max_chars: int = 2000) -> dict:
    """Truncate large values in tool results for storage."""
    truncated = {}
    for key, value in result.items():
        if isinstance(value, str) and len(value) > max_chars:
            truncated[key] = value[:max_chars] + "..."
        else:
            truncated[key] = value
    return truncated
