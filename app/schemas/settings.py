from pydantic import BaseModel


class RoleModelDefaultsResponse(BaseModel):
    leader: str
    executor: str
    reviewer: str | None


class LLMSettingsResponse(BaseModel):
    provider: str
    base_url: str
    read_only: bool
    editable: bool
    leader_model: str
    executor_model: str
    reviewer_model: str | None
    supported_models: list[str]
    default_role_models: RoleModelDefaultsResponse
    legacy_executor_fallback_model: str
    legacy_executor_fallback_active: bool
    timeout_seconds: int
    max_retries: int
