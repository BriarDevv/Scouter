"""Agent orchestration core — runs a single agent turn with tool calling.

The main entry point is ``run_agent_turn`` which streams ``AgentEvent``
objects that the transport layer (SSE, Telegram, WhatsApp) converts to
its native format.
"""

from __future__ import annotations

import functools
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

import app.agent.tools  # noqa: F401 — ensure all tools are registered
from app.agent.events import (
    AgentError,
    AgentEvent,
    ConfirmationRequired,
    TextDelta,
    ToolResult,
    ToolStart,
    TurnComplete,
)
from app.agent.hermes_format import (
    contains_tool_call,
    format_tool_result,
    parse_tool_calls,
)
from app.agent.prompts import build_agent_system_prompt
from app.agent.streaming_client import AgentStreamError, stream_ollama_chat
from app.agent.tool_registry import registry
from app.core.config import settings
from app.core.logging import get_logger
from app.llm.resolver import resolve_model_for_role
from app.llm.roles import LLMRole
from app.models.conversation import Message, ToolCall

logger = get_logger(__name__)

MAX_TOOL_LOOPS = 5
MAX_HISTORY_MESSAGES = 50
# Ollama context window and budget allocation
_CONTEXT_WINDOW = 16384
_RESERVED_FOR_RESPONSE = 2048  # tokens reserved for model output
_CHARS_PER_TOKEN = 4  # conservative estimate for Spanish text


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for Spanish/mixed text."""
    return len(text) // _CHARS_PER_TOKEN


def _trim_history_to_budget(
    system_prompt: str, history: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Trim history from the oldest end to fit within the context window.

    Always preserves the system prompt. Removes oldest messages first.
    """
    budget = _CONTEXT_WINDOW - _RESERVED_FOR_RESPONSE
    system_tokens = _estimate_tokens(system_prompt)
    available = budget - system_tokens

    if available <= 0:
        logger.warning("system_prompt_exceeds_budget", system_tokens=system_tokens)
        return history[-5:]  # keep at least last 5 messages

    # Walk from newest to oldest, accumulating token cost
    kept: list[dict[str, str]] = []
    used = 0
    for msg in reversed(history):
        msg_tokens = _estimate_tokens(msg.get("content", ""))
        if used + msg_tokens > available:
            break
        kept.append(msg)
        used += msg_tokens

    kept.reverse()
    if len(kept) < len(history):
        logger.info(
            "history_trimmed",
            original=len(history),
            kept=len(kept),
            tokens_used=used,
            budget=available,
        )
    return kept


@functools.lru_cache(maxsize=1)
def _cached_tools_schema() -> str:
    """Cache the Hermes tool schema — it never changes at runtime."""
    return registry.to_hermes_schema()


def _build_system_context(db: Session) -> str:
    """Gather a quick stats summary + latest weekly report for the agent's system prompt."""
    parts = []

    try:
        from app.services.dashboard.dashboard_service import get_dashboard_stats

        stats = get_dashboard_stats(db)
        parts.append(
            f"Total leads: {stats['total_leads']} | "
            f"Contactados: {stats['contacted']} | "
            f"Respondieron: {stats['replied']} | "
            f"Ganados: {stats['won']} | "
            f"Score promedio: {stats['avg_score']}"
        )
    except Exception as exc:
        logger.debug("mote_context_stats_failed", error=str(exc))

    # Inject freshest synthesis: batch review (preferred) or weekly report (fallback)
    batch_brief_injected = False
    try:
        from app.services.pipeline.batch_review_service import get_latest_strategy_brief

        brief = get_latest_strategy_brief(db)
        if brief:
            parts.append(f"\nUltima reunion del equipo IA:\n{brief[:1500]}")
            batch_brief_injected = True
    except Exception as exc:
        logger.debug("mote_context_batch_review_failed", error=str(exc))

    if not batch_brief_injected:
        try:
            from app.models.weekly_report import WeeklyReport

            latest = db.query(WeeklyReport).order_by(WeeklyReport.created_at.desc()).first()
            if latest and latest.synthesis_text:
                parts.append(
                    f"\nUltimo reporte semanal del equipo IA:\n{latest.synthesis_text[:1500]}"
                )
        except Exception as exc:
            logger.debug("mote_context_weekly_report_failed", error=str(exc))

    # Inject top correction patterns so Mote can advise on quality
    try:
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import func

        from app.models.review_correction import ReviewCorrection

        cutoff = datetime.now(UTC) - timedelta(days=30)
        top_corrections = (
            db.query(ReviewCorrection.category, func.count().label("cnt"))
            .filter(ReviewCorrection.created_at >= cutoff)
            .group_by(ReviewCorrection.category)
            .order_by(func.count().desc())
            .limit(3)
            .all()
        )
        if top_corrections:
            lines = [f"  - {cat}: {cnt} veces" for cat, cnt in top_corrections]
            parts.append(
                "\nPatrones de correccion del Reviewer (ultimos 30 dias):\n" + "\n".join(lines)
            )
    except Exception as exc:
        logger.debug("mote_context_corrections_failed", error=str(exc))

    return "\n".join(parts)


def _get_model() -> str:
    """Resolve the agent model name."""
    model = resolve_model_for_role(LLMRole.AGENT)
    if not model:
        raise AgentStreamError("No model configured for AGENT role")
    return model


def _load_history(db: Session, conversation_id: uuid.UUID) -> list[dict[str, str]]:
    """Load conversation history as Ollama message dicts."""
    messages = list(
        reversed(
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(MAX_HISTORY_MESSAGES)
            .all()
        )
    )

    history: list[dict[str, str]] = []
    for msg in messages:
        if msg.role in ("user", "assistant"):
            history.append({"role": msg.role, "content": msg.content or ""})
        elif msg.role == "tool":
            # Tool results are injected as user messages with tool_response tags
            history.append({"role": "user", "content": msg.content or ""})
    return history


def _save_message(
    db: Session,
    conversation_id: uuid.UUID,
    role: str,
    content: str | None,
    model: str | None = None,
) -> Message:
    """Persist a message to the database."""
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model=model,
    )
    db.add(msg)
    db.flush()
    return msg


def _json_safe(obj: Any) -> Any:
    """Make an object JSON-serializable (convert UUIDs, datetimes, enums)."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    return obj


def _save_tool_call(
    db: Session,
    message_id: uuid.UUID,
    tool_name: str,
    arguments: dict,
    result: Any = None,
    error: str | None = None,
    status: str = "completed",
    duration_ms: int | None = None,
) -> ToolCall:
    """Persist a tool call record."""
    safe_result = _json_safe(result) if result is not None else None
    tc = ToolCall(
        message_id=message_id,
        tool_name=tool_name,
        arguments_json=arguments,
        result_json=safe_result if isinstance(safe_result, dict) else {"value": safe_result},
        error=error,
        status=status,
        duration_ms=duration_ms,
        completed_at=datetime.now(UTC) if status in ("completed", "failed") else None,
    )
    db.add(tc)
    db.flush()
    return tc


def _suggest_tools(name: str) -> str:
    """Suggest similar tool names when a tool is not found."""
    all_names = [t.name for t in registry.list_all()]
    # Simple substring matching
    matches = [
        n
        for n in all_names
        if name.replace("_", "") in n.replace("_", "")
        or any(w in n for w in name.split("_") if len(w) > 3)
    ]
    if matches:
        return f" Herramientas similares: {', '.join(matches[:5])}"
    return f" Herramientas disponibles: {', '.join(all_names)}"


def _execute_tool(db: Session, tool_name: str, arguments: dict) -> tuple[Any, str | None]:
    """Execute a tool and return (result, error)."""
    tool_def = registry.get(tool_name)
    if not tool_def or not tool_def.handler:
        hint = _suggest_tools(tool_name)
        return None, f"Herramienta '{tool_name}' no existe.{hint}"

    try:
        validated_args = registry.validate_call(tool_name, arguments)
    except (KeyError, ValueError) as exc:
        return None, str(exc)

    try:
        # Use the takes_db flag cached at registration time to avoid calling
        # inspect.signature on every tool invocation.
        if tool_def.takes_db:
            result = tool_def.handler(db, **validated_args)
        else:
            result = tool_def.handler(**validated_args)

        return result, None
    except Exception as exc:
        logger.error("tool_execution_error", tool=tool_name, error=str(exc))
        return None, str(exc)


async def run_agent_turn(
    *,
    conversation_id: uuid.UUID,
    user_message: str,
    db: Session,
    channel: str = "web",
) -> AsyncGenerator[AgentEvent, None]:
    """Run one agent turn: stream response, detect tool calls, execute, loop.

    Yields AgentEvent objects that the transport layer converts to SSE/messages.
    """
    model = _get_model()

    # Save user message
    _save_message(db, conversation_id, "user", user_message)
    db.commit()

    # Build system prompt with live context (schema cached)
    tools_schema = _cached_tools_schema()
    system_context = _build_system_context(db)
    system_prompt = build_agent_system_prompt(tools_schema, system_context=system_context)

    # Load conversation history and trim to fit context window
    history = _load_history(db, conversation_id)
    history = _trim_history_to_budget(system_prompt, history)

    # Ollama messages: system + history
    ollama_messages = [
        {"role": "system", "content": system_prompt},
        *history,
    ]

    for _loop_idx in range(MAX_TOOL_LOOPS):
        # Stream response from Hermes 3
        full_response = ""
        try:
            async for token in stream_ollama_chat(
                model=model,
                messages=ollama_messages,
                timeout=float(settings.OLLAMA_AGENT_TIMEOUT),
            ):
                full_response += token
                yield TextDelta(content=token)
        except AgentStreamError as exc:
            yield AgentError(error=str(exc))
            return

        if not full_response.strip():
            yield AgentError(error="Respuesta vacía del modelo")
            return

        # Check for tool calls in the response
        if not contains_tool_call(full_response):
            # No tool calls — save assistant message and finish
            assistant_msg = _save_message(
                db,
                conversation_id,
                "assistant",
                full_response,
                model=model,
            )
            db.commit()
            yield TurnComplete(message_id=assistant_msg.id)
            return

        # Parse tool calls
        tool_calls = parse_tool_calls(full_response)
        if not tool_calls:
            # Failed to parse — save as regular message
            assistant_msg = _save_message(
                db,
                conversation_id,
                "assistant",
                full_response,
                model=model,
            )
            db.commit()
            yield TurnComplete(message_id=assistant_msg.id)
            return

        # Save assistant message with tool calls
        assistant_msg = _save_message(
            db,
            conversation_id,
            "assistant",
            full_response,
            model=model,
        )

        # Execute each tool call
        tool_results_text = []
        for tc in tool_calls:
            tool_call_id = str(uuid.uuid4())
            tool_def = registry.get(tc.name)

            # Check if confirmation is required
            if tool_def and tool_def.requires_confirmation:
                _save_tool_call(
                    db,
                    assistant_msg.id,
                    tc.name,
                    tc.arguments,
                    status="pending",
                )
                db.commit()
                yield ConfirmationRequired(
                    tool_name=tc.name,
                    tool_call_id=tool_call_id,
                    arguments=tc.arguments,
                    description_es=f"Ejecutar {tc.name} con {tc.arguments}",
                )
                # For now, auto-skip confirmation in the loop
                # (confirmation flow handled separately via API)
                tool_results_text.append(
                    format_tool_result(
                        tc.name,
                        None,
                        error="Acción pendiente de confirmación del usuario",
                    )
                )
                continue

            yield ToolStart(
                tool_name=tc.name,
                tool_call_id=tool_call_id,
                arguments=tc.arguments,
            )

            start_time = time.perf_counter()
            result, error = _execute_tool(db, tc.name, tc.arguments)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            _save_tool_call(
                db,
                assistant_msg.id,
                tc.name,
                tc.arguments,
                result=result,
                error=error,
                status="failed" if error else "completed",
                duration_ms=duration_ms,
            )

            yield ToolResult(
                tool_call_id=tool_call_id,
                tool_name=tc.name,
                result=_json_safe(result),
                error=error,
            )

            tool_results_text.append(format_tool_result(tc.name, result, error))

        db.commit()

        # If all tools needed confirmation, stop the loop
        if all("pendiente de confirmación" in t for t in tool_results_text):
            yield TurnComplete(message_id=assistant_msg.id)
            return

        # Append tool results and re-prompt
        combined_results = "\n".join(tool_results_text)
        _save_message(db, conversation_id, "tool", combined_results)
        db.commit()

        # Rebuild messages for next loop iteration
        ollama_messages.append({"role": "assistant", "content": full_response})
        ollama_messages.append({"role": "user", "content": combined_results})

    # Max loops exceeded
    yield AgentError(error="Se alcanzó el límite máximo de iteraciones de herramientas")
