import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.lead import LeadQuality, LeadStatus
from app.models.outreach import DraftStatus, LogAction


class LeaderPerformanceHighlightsResponse(BaseModel):
    top_industry: str | None = None
    top_city: str | None = None
    top_source: str | None = None


class LeaderOverviewResponse(BaseModel):
    total_leads: int
    qualified: int
    avg_score: float
    conversion_rate: float
    pipeline_velocity: float
    drafts_pending_review: int
    drafts_approved: int
    drafts_recent_24h: int
    pipelines_running: int
    pipelines_failed: int
    pipelines_recent_24h: int
    running_tasks: int
    retrying_tasks: int
    failed_tasks: int
    recent_activity_24h: int
    performance_highlights: LeaderPerformanceHighlightsResponse
    snapshot_at: datetime


class LeaderLeadSummaryResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    industry: str | None
    city: str | None
    status: LeadStatus
    score: float | None
    quality: LeadQuality
    source_name: str | None
    updated_at: datetime


class LeaderDraftSummaryResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    lead_name: str | None
    status: DraftStatus
    subject: str
    generated_at: datetime
    reviewed_at: datetime | None
    sent_at: datetime | None


class LeaderPipelineSummaryResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    lead_name: str | None
    status: str
    current_step: str | None
    root_task_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class LeaderTaskSummaryResponse(BaseModel):
    task_id: str
    task_name: str
    queue: str | None
    lead_id: uuid.UUID | None
    lead_name: str | None
    pipeline_run_id: uuid.UUID | None
    status: str
    current_step: str | None
    correlation_id: str | None
    error: str | None
    updated_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None


class LeaderTaskHealthResponse(BaseModel):
    running_count: int
    retrying_count: int
    failed_count: int
    running: list[LeaderTaskSummaryResponse]
    retrying: list[LeaderTaskSummaryResponse]
    failed: list[LeaderTaskSummaryResponse]


class LeaderActivityItemResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    lead_name: str | None
    draft_id: uuid.UUID | None
    action: LogAction
    actor: str
    detail: str | None
    created_at: datetime


class LeaderReplySummaryResponse(BaseModel):
    since_hours: int
    since_at: datetime
    snapshot_at: datetime
    latest_reply_at: datetime | None
    total_recent_replies: int
    replied_leads: int
    positive_replies: int
    interested_replies: int
    quote_replies: int
    meeting_replies: int
    reviewer_candidates: int
    important_replies: int
    pending_classification: int
    failed_classification: int
    unmatched_replies: int


class LeaderReplyItemResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    lead_name: str | None
    draft_id: uuid.UUID | None
    delivery_id: uuid.UUID | None
    from_email: str | None
    subject: str | None
    body_snippet: str | None
    classification_status: str
    classification_label: str | None
    summary: str | None
    confidence: float | None
    next_action_suggestion: str | None
    should_escalate_reviewer: bool
    matched_via: str
    match_confidence: float | None
    received_at: datetime | None
    classification_role: str | None
    classification_model: str | None
    priority_score: int
