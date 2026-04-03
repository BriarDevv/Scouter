import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskEnqueueResponse(BaseModel):
    task_id: str
    status: str
    queue: str | None = None
    lead_id: uuid.UUID | None = None
    pipeline_run_id: uuid.UUID | None = None
    current_step: str | None = None


class TaskStatusResponse(TaskEnqueueResponse):
    correlation_id: str | None = None
    scope_key: str | None = None
    progress_json: dict | None = None
    result: dict | None = None
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    stop_requested_at: datetime | None = None


class PipelineRunSummaryResponse(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    correlation_id: str
    root_task_id: str | None
    status: str
    current_step: str | None
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class PipelineRunDetailResponse(PipelineRunSummaryResponse):
    tasks: list[TaskStatusResponse]
