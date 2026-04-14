"""Periodic janitor package — replaces the old monolithic janitor.py.

Public surface is unchanged: every name that used to be importable from
`app.workers.janitor.*` is re-exported here. The two Celery task
decorators live in this __init__ so the registered task names remain
`app.workers.janitor.task_sweep_stale` and
`app.workers.janitor.task_drain_dead_letter`.
"""

from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.janitor.dlq import (
    _REPLAYABLE_PIPELINE_TASKS,
    DLQ_REPLAY_BATCH_LIMIT,
    DLQ_REPLAY_WINDOW_HOURS,
    drain_dead_letter_queue,
)
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
    "DLQ_REPLAY_BATCH_LIMIT",
    "DLQ_REPLAY_WINDOW_HOURS",
    "MAX_PIPELINE_RETRIES",
    "ORPHAN_THRESHOLD",
    "PIPELINE_STALE_THRESHOLD",
    "STALE_THRESHOLD",
    "_REPLAYABLE_PIPELINE_TASKS",
    "_auto_resume_pipeline",
    "_check_pipeline_inactive",
    "_is_retryable_error",
    "drain_dead_letter_queue",
    "sweep_orphan_pipelines",
    "sweep_stale_tasks",
    "sweep_stuck_research_reports",
    "sweep_zombie_leads",
    "task_drain_dead_letter",
    "task_sweep_stale",
]


@celery_app.task(name="app.workers.janitor.task_sweep_stale")
def task_sweep_stale() -> dict:
    """Celery-wrapped janitor for use with celery beat."""
    return sweep_stale_tasks()


@celery_app.task(name="app.workers.janitor.task_drain_dead_letter")
def task_drain_dead_letter() -> dict:
    """Celery-wrapped DLQ replay for use with celery beat."""
    return drain_dead_letter_queue()
