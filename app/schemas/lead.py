import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.lead import LeadQuality, LeadStatus
from app.models.lead_signal import SignalType
from app.models.lead_source import SourceType


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
    address: str | None = None
    google_maps_url: str | None = None
    rating: float | None = None
    review_count: int | None = None
    business_status: str | None = Field(None, max_length=50)
    opening_hours: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class LeadUpdate(BaseModel):
    business_name: str | None = Field(None, max_length=500)
    industry: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=255)
    zone: str | None = Field(None, max_length=255)
    website_url: str | None = None
    instagram_url: str | None = None
    email: str | None = Field(None, max_length=320)
    phone: str | None = Field(None, max_length=50)


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


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
    status: LeadStatus
    score: float | None
    quality: LeadQuality
    llm_summary: str | None
    llm_quality_assessment: str | None
    llm_suggested_angle: str | None
    address: str | None
    google_maps_url: str | None
    rating: float | None
    review_count: int | None
    business_status: str | None
    opening_hours: str | None
    latitude: float | None
    longitude: float | None
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
    signal_type: SignalType
    detail: str | None
    detected_at: datetime


class LeadSourceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    source_type: SourceType
    url: str | None
    description: str | None
    created_at: datetime


class LeadDetailResponse(LeadResponse):
    signals: list[LeadSignalResponse] = Field(default_factory=list)
    source: LeadSourceResponse | None = None


class LeadNameResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    business_name: str
