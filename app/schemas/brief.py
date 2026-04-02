"""Commercial brief schemas."""

from datetime import datetime

from pydantic import BaseModel


class CommercialBriefResponse(BaseModel):
    id: str
    lead_id: str
    status: str
    opportunity_score: float | None = None
    budget_tier: str | None = None
    estimated_budget_min: float | None = None
    estimated_budget_max: float | None = None
    estimated_scope: str | None = None
    recommended_contact_method: str | None = None
    should_call: str | None = None
    call_reason: str | None = None
    why_this_lead_matters: str | None = None
    main_business_signals: list | None = None
    main_digital_gaps: list | None = None
    recommended_angle: str | None = None
    demo_recommended: bool | None = None
    contact_priority: str | None = None
    generator_model: str | None = None
    reviewer_model: str | None = None
    reviewed_at: datetime | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
