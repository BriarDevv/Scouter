from pydantic import BaseModel

from app.models.lead import LeadStatus


class DashboardStatsResponse(BaseModel):
    total_leads: int
    new_today: int
    qualified: int
    approved: int
    contacted: int
    replied: int
    meetings: int
    won: int
    lost: int
    suppressed: int
    avg_score: float
    conversion_rate: float
    open_rate: float
    reply_rate: float
    positive_reply_rate: float
    meeting_rate: float
    pipeline_velocity: float


class PipelineStageResponse(BaseModel):
    stage: LeadStatus
    label: str
    count: int
    percentage: float
    color: str


class TimeSeriesPointResponse(BaseModel):
    date: str
    leads: int
    outreach: int
    replies: int
    conversions: int


class IndustryBreakdownResponse(BaseModel):
    industry: str
    count: int
    avg_score: float
    conversion_rate: float


class CityBreakdownResponse(BaseModel):
    city: str
    count: int
    avg_score: float
    reply_rate: float


class SourcePerformanceResponse(BaseModel):
    source: str
    leads: int
    avg_score: float
    reply_rate: float
    conversion_rate: float
