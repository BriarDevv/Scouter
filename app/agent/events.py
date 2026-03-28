"""Agent event types used by the orchestration loop and streamed to clients.

Each event is an immutable dataclass that represents a discrete step in the
agent turn lifecycle: streaming text, tool invocation, confirmation gates,
completion, and errors.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Base class for agent events."""


@dataclass(frozen=True, slots=True)
class TextDelta(AgentEvent):
    """Streaming text chunk from the agent."""

    content: str


@dataclass(frozen=True, slots=True)
class ToolStart(AgentEvent):
    """Agent is about to execute a tool."""

    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult(AgentEvent):
    """Result from a tool execution."""

    tool_call_id: str
    tool_name: str
    result: Any
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ConfirmationRequired(AgentEvent):
    """A destructive tool needs human confirmation before executing."""

    tool_name: str
    tool_call_id: str
    arguments: dict[str, Any]
    description_es: str


@dataclass(frozen=True, slots=True)
class TurnComplete(AgentEvent):
    """Agent turn finished successfully."""

    message_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class AgentError(AgentEvent):
    """An error occurred during the agent turn."""

    error: str
