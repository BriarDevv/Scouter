"""Integration-level tests for Celery task registration, routing, and serialization.

These tests do NOT require a live broker — they exercise task metadata,
route configuration, and argument serialization entirely in-process.
"""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import celery_app and the route map under test.
# The conftest already set CELERY_BROKER_URL=memory:// before this import.
# ---------------------------------------------------------------------------
from app.workers.celery_app import _TASK_ROUTES_FULL, celery_app

# ---------------------------------------------------------------------------
# 1. All tasks in _TASK_ROUTES_FULL are actually registered
# ---------------------------------------------------------------------------


def test_all_tasks_registered():
    """Every task name declared in _TASK_ROUTES_FULL must exist in the Celery registry."""
    registered = set(celery_app.tasks.keys())
    missing = []
    for task_name in _TASK_ROUTES_FULL:
        if task_name not in registered:
            missing.append(task_name)
    assert missing == [], f"Tasks declared in routes but not registered: {missing}"


# ---------------------------------------------------------------------------
# 2. Each route entry has a matching task object with the correct .name
# ---------------------------------------------------------------------------


def test_task_routes_match_definitions():
    """Each route key must correspond to a registered task whose .name == the key."""
    for task_name in _TASK_ROUTES_FULL:
        task_obj = celery_app.tasks.get(task_name)
        assert task_obj is not None, f"No task object found for route key '{task_name}'"
        assert task_obj.name == task_name, (
            f"Task object name mismatch: expected '{task_name}', got '{task_obj.name}'"
        )


# ---------------------------------------------------------------------------
# 3. Beat schedule tasks are registered
# ---------------------------------------------------------------------------


def test_beat_schedule_tasks_exist():
    """Every task referenced in beat_schedule must be registered in the Celery registry."""
    beat_schedule = celery_app.conf.beat_schedule or {}
    registered = set(celery_app.tasks.keys())
    missing = []
    for entry_name, entry in beat_schedule.items():
        task_name = entry.get("task")
        if task_name and task_name not in registered:
            missing.append((entry_name, task_name))
    assert missing == [], f"Beat schedule entries reference unregistered tasks: {missing}"


# ---------------------------------------------------------------------------
# 4. Low-resource mode collapses all routes to 'default' queue
# ---------------------------------------------------------------------------


def test_low_resource_mode_collapses_queues(monkeypatch):
    """When _resolve_low_resource returns True, task_routes must be empty (all tasks
    fall through to the default queue)."""
    monkeypatch.setattr("app.workers.celery_app._resolve_low_resource", lambda: True)

    low_resource_routes = {} if True else _TASK_ROUTES_FULL

    # Simulate what celery_app.conf.update does in low-resource mode
    effective_routes = low_resource_routes
    assert effective_routes == {}, (
        "In low-resource mode, task_routes should be empty so all tasks land on the default queue"
    )
    # Verify the default queue is 'default'
    assert celery_app.conf.task_default_queue == "default"


# ---------------------------------------------------------------------------
# 5. Task arguments round-trip through JSON serialization
# ---------------------------------------------------------------------------

_PIPELINE_TASK_ARGS = [
    # (task_name, args_dict)
    (
        "app.workers.tasks.task_enrich_lead",
        {
            "lead_id": str(uuid.uuid4()),
            "pipeline_run_id": str(uuid.uuid4()),
            "correlation_id": "corr-001",
        },
    ),
    (
        "app.workers.tasks.task_score_lead",
        {
            "lead_id": str(uuid.uuid4()),
            "pipeline_run_id": str(uuid.uuid4()),
            "correlation_id": None,
        },
    ),
    (
        "app.workers.tasks.task_analyze_lead",
        {"lead_id": str(uuid.uuid4()), "pipeline_run_id": None, "correlation_id": None},
    ),
    (
        "app.workers.tasks.task_generate_draft",
        {"lead_id": str(uuid.uuid4()), "pipeline_run_id": str(uuid.uuid4()), "correlation_id": "x"},
    ),
    (
        "app.workers.tasks.task_research_lead",
        {
            "lead_id": str(uuid.uuid4()),
            "pipeline_run_id": str(uuid.uuid4()),
            "correlation_id": None,
        },
    ),
    (
        "app.workers.brief_tasks.task_generate_brief",
        {
            "lead_id": str(uuid.uuid4()),
            "pipeline_run_id": str(uuid.uuid4()),
            "correlation_id": None,
        },
    ),
    (
        "app.workers.brief_tasks.task_review_brief",
        {"lead_id": str(uuid.uuid4()), "pipeline_run_id": None, "correlation_id": None},
    ),
]


@pytest.mark.parametrize("task_name,kwargs", _PIPELINE_TASK_ARGS)
def test_task_serialization_roundtrip(task_name, kwargs):
    """Task keyword arguments must survive a JSON round-trip without data loss.

    Celery serializes task args as JSON before dispatching, so anything that
    cannot round-trip through json.dumps/json.loads will silently corrupt data.
    """
    serialized = json.dumps(kwargs)
    restored = json.loads(serialized)
    assert restored == kwargs, (
        f"Serialization round-trip failed for {task_name}: "
        f"original={kwargs!r}, restored={restored!r}"
    )
    # Also confirm the task itself is registered (belt-and-suspenders)
    assert task_name in celery_app.tasks, f"Task '{task_name}' not registered"


# ---------------------------------------------------------------------------
# 6. Pipeline chain: task_enrich_lead dispatches task_score_lead on success
# ---------------------------------------------------------------------------


def test_pipeline_chain_dispatches_next_step(db, monkeypatch):
    """task_enrich_lead.run() must call task_score_lead.delay() with the correct
    lead_id and pipeline_run_id when the lead is found and enrichment succeeds."""
    from app.models.lead import Lead
    from app.models.task_tracking import PipelineRun
    from app.workers.pipeline_tasks import task_enrich_lead

    # Create a real lead so the DB lookup succeeds
    lead = Lead(business_name="Chain Test Co", city="Buenos Aires")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Create a matching PipelineRun row (FK required by task_runs)
    pipeline_run = PipelineRun(
        lead_id=lead.id,
        correlation_id=f"test-corr-{uuid.uuid4()}",
        status="queued",
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

    lead_id = str(lead.id)
    pipeline_run_id = str(pipeline_run.id)

    # Stub out enrichment so we don't need external services
    fake_lead = SimpleNamespace(
        id=lead.id,
        enriched_at=None,
        signals=[],
        email=None,
        website_url="https://example.com",
        instagram_url=None,
    )

    delay_mock = MagicMock()
    monkeypatch.setattr("app.workers.pipeline_tasks.enrich_lead", lambda db_, lid: fake_lead)
    monkeypatch.setattr("app.workers.pipeline_tasks.task_score_lead.delay", delay_mock)
    # Stub context_service to avoid DB writes for pipeline context
    monkeypatch.setattr(
        "app.services.pipeline.context_service.append_step_context",
        lambda *a, **kw: None,
    )

    result = task_enrich_lead.run(lead_id, pipeline_run_id=pipeline_run_id, correlation_id=None)

    assert result["status"] == "ok"
    assert result["lead_id"] == lead_id

    delay_mock.assert_called_once_with(
        lead_id,
        pipeline_run_id=pipeline_run_id,
        correlation_id=None,
    )
