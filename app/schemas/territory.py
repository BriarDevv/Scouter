"""Territory request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TerritoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    cities: list[str] = Field(default_factory=list)
    is_active: bool = True


class TerritoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    cities: list[str] | None = None
    is_active: bool | None = None


class TerritoryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    color: str
    cities: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TerritoryWithStats(TerritoryResponse):
    lead_count: int = 0
    avg_score: float = 0.0
    qualified_count: int = 0
    conversion_rate: float = 0.0
