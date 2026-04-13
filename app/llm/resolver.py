from __future__ import annotations

from typing import TYPE_CHECKING

from app.llm.roles import LLMRole

if TYPE_CHECKING:
    from app.core.config import Settings


def normalize_role(role: LLMRole | str) -> LLMRole:
    if isinstance(role, LLMRole):
        return role
    return LLMRole(role)


def resolve_model_for_role(role: LLMRole | str, config: Settings | None = None) -> str | None:
    if config is None:
        from app.core.config import settings

        config = settings
    normalized_role = normalize_role(role)
    return config.ollama_models_by_role[normalized_role]
