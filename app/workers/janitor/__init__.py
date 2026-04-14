"""Periodic janitor package — replaces the old monolithic janitor.py.

Public surface is unchanged: every name that used to be importable from
`app.workers.janitor.*` is re-exported here. The Celery task decorator
lives in this __init__ so the registered task name remains
`app.workers.janitor.task_sweep_stale`.
"""

from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.janitor.orchestrator import sweep_stale_tasks
from app.workers.janitor.stale import (
    ACTIVE_STATUSES,
    MAX_PIPELINE_RETRIES,
    ORPHAN_THRESHOLD,
    PIPELINE_STALE_THRESHOLD,
    STALE_THRESHOLD,
    _auto_resume_pipeline,
    _check_pipeline_inactive,
    _is_retryable_error,
    sweep_orphan_pipelines,
)
from app.workers.janitor.zombies import (
    sweep_stuck_research_reports,
    sweep_zombie_leads,
)

__all__ = [
    "ACTIVE_STATUSES",
    "MAX_PIPELINE_RETRIES",
    "ORPHAN_THRESHOLD",
    "PIPELINE_STALE_THRESHOLD",
    "STALE_THRESHOLD",
    "_auto_resume_pipeline",
    "_check_pipeline_inactive",
    "_is_retryable_error",
    "sweep_orphan_pipelines",
    "sweep_stale_tasks",
    "sweep_stuck_research_reports",
    "sweep_zombie_leads",
    "task_sweep_stale",
]


@celery_app.task(name="app.workers.janitor.task_sweep_stale")
def task_sweep_stale() -> dict:
    """Celery-wrapped janitor for use with celery beat."""
    return sweep_stale_tasks()
