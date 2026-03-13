import uuid

from pydantic import BaseModel

from app.llm.roles import LLMRole


class LeadReviewResponse(BaseModel):
    lead_id: uuid.UUID
    business_name: str
    role: LLMRole
    model: str
    verdict: str
    confidence: str
    reasoning: str
    recommended_action: str
    watchouts: list[str]


class DraftReviewResponse(BaseModel):
    draft_id: uuid.UUID
    lead_id: uuid.UUID
    business_name: str
    role: LLMRole
    model: str
    verdict: str
    confidence: str
    reasoning: str
    strengths: list[str]
    concerns: list[str]
    suggested_changes: list[str]
    revised_subject: str | None
    revised_body: str | None


class InboundReplyReviewResponse(BaseModel):
    inbound_message_id: uuid.UUID
    thread_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    business_name: str | None
    role: LLMRole
    model: str
    classification_label: str | None
    verdict: str
    confidence: str
    reasoning: str
    recommended_action: str
    suggested_response_angle: str | None
    watchouts: list[str]
