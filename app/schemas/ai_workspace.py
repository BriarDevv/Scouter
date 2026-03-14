from pydantic import BaseModel, Field


class AIWorkspaceFileStatus(BaseModel):
    key: str
    filename: str
    exists: bool
    size_bytes: int | None = None
    last_modified: str | None = None
    is_empty: bool = False
    has_valid_structure: bool = True
    warnings: list[str] = Field(default_factory=list)
    preview: str | None = None
    editable: bool = True


class AIWorkspaceSkill(BaseModel):
    name: str
    description: str | None = None
    path: str
    exists: bool


class AIWorkspaceModels(BaseModel):
    leader: str
    executor: str
    reviewer: str | None = None


class AIWorkspaceStatusResponse(BaseModel):
    files: list[AIWorkspaceFileStatus]
    skills: list[AIWorkspaceSkill]
    models: AIWorkspaceModels
    workspace_path: str
    openclaw_installed: bool
    onboarding_completed: bool


class AIWorkspaceFileContent(BaseModel):
    key: str
    filename: str
    content: str | None = None
    exists: bool


class AIWorkspaceFileUpdate(BaseModel):
    content: str = Field(..., max_length=51200)


class AIWorkspaceFileResetResponse(BaseModel):
    key: str
    filename: str
    content: str
    exists: bool = True
    reset: bool = True
