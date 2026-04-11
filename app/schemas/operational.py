"""Pydantic response schemas for operational task control endpoints (rescore-all, batch
pipeline)."""

from pydantic import BaseModel


class TaskQueuedResponse(BaseModel):
    task_id: str
    status: str
    correlation_id: str | None = None
    message: str | None = None


class TaskStopResponse(BaseModel):
    ok: bool
    message: str


class RescoreAllStatusResponse(BaseModel):
    status: str
    task_id: str | None = None
    total: int | None = None
    rescored: int | None = None
    errors: int | None = None
    current_lead_id: str | None = None
    current_step: str | None = None
    error: str | None = None
    correlation_id: str | None = None


class BatchPipelineStatusResponse(BaseModel):
    status: str
    task_id: str | None = None
    total: int | None = None
    processed: int | None = None
    current_lead: str | None = None
    current_step: str | None = None
    errors: int | None = None
    crawl_rounds: int | None = None
    leads_from_crawl: int | None = None
    error: str | None = None
    correlation_id: str | None = None


class BatchPipelineStartResponse(BaseModel):
    ok: bool
    message: str
    task_id: str | None = None
    correlation_id: str | None = None
    progress: BatchPipelineStatusResponse | None = None
