import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class LeadCreate(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=500)
    industry: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=255)
    zone: str | None = Field(None, max_length=255)
    website_url: str | None = None
    instagram_url: str | None = None
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=50)
    source_id: uuid.UUID | None = None


class LeadUpdate(BaseModel):
    business_name: str | None = Field(None, max_length=500)
    industry: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=255)
    zone: str | None = Field(None, max_length=255)
    website_url: str | None = None
    instagram_url: str | None = None
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=50)


class LeadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    business_name: str
    industry: str | None
    city: str | None
    zone: str | None
    website_url: str | None
    instagram_url: str | None
    email: str | None
    phone: str | None
    source_id: uuid.UUID | None
    status: str
    score: float | None
    llm_summary: str | None
    llm_quality_assessment: str | None
    llm_suggested_angle: str | None
    dedup_hash: str | None
    created_at: datetime
    updated_at: datetime
    enriched_at: datetime | None
    scored_at: datetime | None


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int


class LeadSignalResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    signal_type: str
    detail: str | None
    detected_at: datetime


class LeadDetailResponse(LeadResponse):
    signals: list[LeadSignalResponse] = []
