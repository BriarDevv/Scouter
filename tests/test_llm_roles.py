from pydantic import ValidationError

from app.core.config import Settings
from app.llm.resolver import normalize_role
from app.llm.roles import LLMRole


def test_settings_uses_legacy_ollama_model_as_executor_fallback():
    settings = Settings(
        OLLAMA_MODEL="qwen3.5:9b",
        OLLAMA_EXECUTOR_MODEL=None,
        OLLAMA_SUPPORTED_MODELS="qwen3.5:4b,qwen3.5:9b,qwen3.5:27b,hermes3:8b",
    )

    assert settings.ollama_executor_model == "qwen3.5:9b"
    assert settings.ollama_models_by_role[LLMRole.EXECUTOR] == "qwen3.5:9b"


def test_settings_prefers_explicit_executor_role_model():
    settings = Settings(
        OLLAMA_MODEL="qwen3.5:9b",
        OLLAMA_EXECUTOR_MODEL="qwen3.5:4b",
        OLLAMA_SUPPORTED_MODELS="qwen3.5:4b,qwen3.5:9b,qwen3.5:27b,hermes3:8b",
    )

    assert settings.ollama_executor_model == "qwen3.5:4b"


def test_settings_rejects_models_outside_supported_catalog():
    try:
        Settings(
            OLLAMA_SUPPORTED_MODELS="qwen3.5:4b,qwen3.5:9b,qwen3.5:27b,hermes3:8b",
            OLLAMA_LEADER_MODEL="llama3:8b",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("Expected invalid role model to raise ValidationError")


def test_settings_normalizes_supported_model_catalog():
    settings = Settings(
        OLLAMA_SUPPORTED_MODELS=" qwen3.5:4b, qwen3.5:9b ,qwen3.5:9b, qwen3.5:27b ",
    )

    assert settings.ollama_supported_models == (
        "qwen3.5:4b",
        "qwen3.5:9b",
        "qwen3.5:27b",
    )


def test_normalize_role_accepts_strings_and_enum():
    assert normalize_role("leader") == LLMRole.LEADER
    assert normalize_role(LLMRole.REVIEWER) == LLMRole.REVIEWER
