from app.llm.roles import LLMRole


DEFAULT_SUPPORTED_MODELS = (
    "qwen3.5:4b",
    "qwen3.5:9b",
    "qwen3.5:27b",
)

DEFAULT_ROLE_MODEL_MAP = {
    LLMRole.LEADER: "qwen3.5:4b",
    LLMRole.EXECUTOR: "qwen3.5:9b",
    LLMRole.REVIEWER: "qwen3.5:27b",
}


def parse_supported_models(raw_models: str) -> tuple[str, ...]:
    unique_models: list[str] = []
    for model_name in raw_models.split(","):
        normalized = model_name.strip()
        if normalized and normalized not in unique_models:
            unique_models.append(normalized)
    return tuple(unique_models)
