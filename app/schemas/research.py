"""Research report schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class ResearchReportResponse(BaseModel):
    id: UUID
    lead_id: UUID
    status: str
    website_exists: bool | None = None
    website_url_verified: str | None = None
    website_confidence: str | None = None
    instagram_exists: bool | None = None
    instagram_url_verified: str | None = None
    instagram_confidence: str | None = None
    whatsapp_detected: bool | None = None
    whatsapp_confidence: str | None = None
    screenshots_json: list | None = None
    detected_signals_json: list | None = None
    html_metadata_json: dict | None = None
    business_description: str | None = None
    researcher_model: str | None = None
    research_duration_ms: int | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("id", "lead_id")
    @classmethod
    def serialize_uuid(cls, v: UUID) -> str:
        return str(v)
