from pydantic import BaseModel


class SetupReadinessStepResponse(BaseModel):
    id: str
    label: str
    status: str
    detail: str | None = None
    action: str | None = None
    required: bool = True


class SetupActionResponse(BaseModel):
    id: str
    label: str
    kind: str
    description: str
    endpoint: str | None = None
    method: str = "POST"
    manual_instructions: str | None = None


class SetupUpdateStatusResponse(BaseModel):
    supported: bool
    current_branch: str | None = None
    updates_available: bool = False
    dirty: bool = False
    can_autopull: bool = False
    detail: str | None = None


class SetupReadinessResponse(BaseModel):
    overall: str
    dashboard_unlocked: bool
    hermes_unlocked: bool
    target_platform: str
    current_platform: str
    recommended_route: str
    summary: str
    platform_steps: list[SetupReadinessStepResponse]
    runtime_steps: list[SetupReadinessStepResponse]
    config_steps: list[SetupReadinessStepResponse]
    wizard_steps: list[str]
    actions: list[SetupActionResponse]
    updates: SetupUpdateStatusResponse


class SetupActionResultResponse(BaseModel):
    action_id: str
    status: str
    summary: str
    detail: str | None = None
    stdout_tail: str | None = None
    manual_instructions: str | None = None
