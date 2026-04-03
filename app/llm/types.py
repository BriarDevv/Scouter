from enum import StrEnum


class LLMInvocationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    DEGRADED = "degraded"
    FALLBACK = "fallback"
    PARSE_FAILED = "parse_failed"
    FAILED = "failed"
