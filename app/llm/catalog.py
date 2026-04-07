"""LLM model catalog — defaults and supported model parsing."""

from app.core.config import LLMRole, parse_supported_models

DEFAULT_SUPPORTED_MODELS = (
    "qwen3.5:9b",
    "qwen3.5:27b",
    "hermes3:8b",
)

DEFAULT_ROLE_MODEL_MAP = {
    LLMRole.LEADER: None,
    LLMRole.EXECUTOR: "qwen3.5:9b",
    LLMRole.REVIEWER: "qwen3.5:27b",
    LLMRole.AGENT: "hermes3:8b",
}

__all__ = [
    "DEFAULT_SUPPORTED_MODELS",
    "DEFAULT_ROLE_MODEL_MAP",
    "parse_supported_models",
]
