"""Per-call metadata for the most recent public LLM invocation."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass, field

from app.llm.types import LLMInvocationStatus


@dataclass(slots=True)
class LLMInvocationMetadata:
    function_name: str
    prompt_id: str
    prompt_version: str
    role: str
    status: LLMInvocationStatus
    model: str | None
    fallback_used: bool
    degraded: bool
    parse_valid: bool = False
    latency_ms: int | None = None
    error: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_last_invocation: ContextVar[LLMInvocationMetadata | None] = ContextVar(
    "llm_last_invocation_metadata",
    default=None,
)


def record_invocation(metadata: LLMInvocationMetadata) -> None:
    _last_invocation.set(metadata)


def peek_last_invocation() -> LLMInvocationMetadata | None:
    return _last_invocation.get()


def pop_last_invocation() -> LLMInvocationMetadata | None:
    metadata = _last_invocation.get()
    _last_invocation.set(None)
    return metadata


def clear_last_invocation() -> None:
    _last_invocation.set(None)
