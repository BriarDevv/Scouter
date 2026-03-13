from app.core.config import settings
from app.llm.catalog import DEFAULT_ROLE_MODEL_MAP
from app.llm.roles import LLMRole


def get_llm_settings() -> dict:
    executor_override = (settings.OLLAMA_EXECUTOR_MODEL or "").strip()

    return {
        "provider": "ollama",
        "base_url": settings.OLLAMA_BASE_URL,
        "read_only": True,
        "editable": False,
        "leader_model": settings.ollama_leader_model,
        "executor_model": settings.ollama_executor_model,
        "reviewer_model": settings.ollama_reviewer_model,
        "supported_models": list(settings.ollama_supported_models),
        "default_role_models": {
            "leader": DEFAULT_ROLE_MODEL_MAP[LLMRole.LEADER],
            "executor": DEFAULT_ROLE_MODEL_MAP[LLMRole.EXECUTOR],
            "reviewer": DEFAULT_ROLE_MODEL_MAP[LLMRole.REVIEWER],
        },
        "legacy_executor_fallback_model": settings.OLLAMA_MODEL.strip(),
        "legacy_executor_fallback_active": not executor_override,
        "timeout_seconds": settings.OLLAMA_TIMEOUT,
        "max_retries": settings.OLLAMA_MAX_RETRIES,
    }
