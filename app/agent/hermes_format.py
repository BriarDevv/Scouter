"""Parsing and formatting for Hermes 3 native tool-calling format.

Hermes 3 uses XML-delimited tool calls and tool responses::

    <tool_call>
    {"name": "search_leads", "arguments": {"query": "..."}}
    </tool_call>

    <tool_response>
    {"name": "search_leads", "content": "..."}
    </tool_response>

This module provides helpers to parse, format, and assemble prompts that
follow this convention.
"""

from __future__ import annotations

import json
import re
from typing import Any, NamedTuple

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ToolCallRequest(NamedTuple):
    """A parsed tool call extracted from Hermes 3 formatted text."""

    name: str
    arguments: dict[str, Any]


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def contains_tool_call(text: str) -> bool:
    """Quick check for the presence of a ``<tool_call>`` tag."""
    return "<tool_call>" in text


def parse_tool_calls(text: str) -> list[ToolCallRequest]:
    """Extract tool calls from Hermes 3 formatted text.

    Supports both ``"arguments"`` and ``"parameters"`` keys for robustness
    (some fine-tunes emit ``parameters`` instead of ``arguments``).

    Returns a list of :class:`ToolCallRequest` named tuples.  Malformed
    blocks are logged and skipped rather than raising.
    """
    results: list[ToolCallRequest] = []

    for match in _TOOL_CALL_RE.finditer(text):
        raw_json = match.group(1)
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning("tool_call_parse_failed", raw=raw_json[:200])
            continue

        name = data.get("name")
        if not name or not isinstance(name, str):
            logger.warning("tool_call_missing_name", data=data)
            continue

        # Accept both "arguments" and "parameters"
        arguments = data.get("arguments") or data.get("parameters") or {}
        if not isinstance(arguments, dict):
            logger.warning(
                "tool_call_invalid_arguments",
                tool_name=name,
                arguments_type=type(arguments).__name__,
            )
            arguments = {}

        results.append(ToolCallRequest(name=name, arguments=arguments))

    return results


def format_tool_result(
    name: str,
    result: Any,
    error: str | None = None,
) -> str:
    """Format a tool result as a Hermes 3 ``<tool_response>`` block.

    If *error* is provided, the content is replaced with an error payload.
    """
    if error is not None:
        payload: dict[str, Any] = {
            "name": name,
            "content": None,
            "error": error,
        }
    else:
        payload = {
            "name": name,
            "content": result,
        }

    return (
        "<tool_response>\n"
        + json.dumps(payload, ensure_ascii=False, default=str)
        + "\n</tool_response>"
    )
