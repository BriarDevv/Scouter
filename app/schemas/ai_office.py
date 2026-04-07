"""Pydantic schemas for the AI Office endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class TestWhatsAppBody(BaseModel):
    phone: str = Field(..., description="Phone in E.164 format (e.g. +5491158399708)")
    message: str = Field(
        default=(
            "Hola! Esto es una prueba de Mote, el agente de Scouter. "
            "Si recibiste esto, el outreach funciona correctamente."
        ),
        max_length=500,
    )


class CloserReplyBody(BaseModel):
    client_message: str = Field(..., description="Client's inbound message")


# --- Response schemas ---


class MoteAgentStatus(BaseModel):
    name: str
    role: str
    model: str
    status: str
    last_active: str | None
    active_conversations: int


class ScoutAgentStatus(BaseModel):
    name: str
    role: str
    model: str
    status: str
    active_investigations: int
    investigations_24h: int


class ExecutorAgentStatus(BaseModel):
    name: str
    role: str
    model: str
    status: str
    invocations_24h: int
    fallback_rate: float


class ReviewerAgentStatus(BaseModel):
    name: str
    role: str
    model: str
    status: str
    invocations_24h: int
    approval_rate: float
    corrections_7d: int


class AgentsStatus(BaseModel):
    mote: MoteAgentStatus
    scout: ScoutAgentStatus
    executor: ExecutorAgentStatus
    reviewer: ReviewerAgentStatus


class OutcomesOverview(BaseModel):
    total_won: int
    total_lost: int


class AgentStatusResponse(BaseModel):
    agents: AgentsStatus
    outcomes: OutcomesOverview


class DecisionItem(BaseModel):
    id: str
    function_name: str | None
    role: str | None
    model: str | None
    status: str | None
    latency_ms: int | None
    fallback_used: bool | None
    target_type: str | None
    target_id: str | None
    prompt_id: str | None
    prompt_version: str | None
    created_at: str | None


class InvestigationItem(BaseModel):
    id: str
    lead_id: str
    agent_model: str | None
    pages_visited: list[Any] | None
    findings: list[Any] | None
    loops_used: int | None
    duration_ms: int | None
    error: str | None
    created_at: str | None


class OutboundConversationItem(BaseModel):
    id: str
    lead_id: str
    channel: str | None
    status: str
    mode: str | None
    messages_count: int
    operator_took_over: bool | None
    error: str | None
    created_at: str | None
    updated_at: str | None


class ConversationDetailResponse(BaseModel):
    id: str
    lead_id: str
    draft_id: str | None
    channel: str | None
    status: str
    mode: str | None
    messages: list[Any]
    operator_took_over: bool | None
    provider_message_id: str | None
    error: str | None
    created_at: str | None
