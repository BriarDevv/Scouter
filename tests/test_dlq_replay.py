"""Regression tests for the Dead Letter Queue replay task.

Closes the gap documented in docs/audits/repo-deep-audit.md section 6:
DeadLetterTask rows used to accumulate forever because there was no
automated replay pass. This module verifies:

- recent + replayable entries are redispatched and marked replayed_at
- unknown task names are skipped (no raise) and marked replayed_at
- stale entries (>24h) are ignored by the sweep
- entries missing lead_id are marked but not replayed
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.dead_letter import DeadLetterTask


def _make_dlq(
    db,
    *,
    task_name: str,
    lead_id: uuid.UUID | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
    payload: dict | None = None,
) -> DeadLetterTask:
    entry = DeadLetterTask(
        task_name=task_name,
        lead_id=lead_id,
        pipeline_run_id=pipeline_run_id,
        step="test",
        error="test failure",
        payload=payload or {"correlation_id": "corr-test"},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    if created_at is not None:
        entry.created_at = created_at
        db.commit()
        db.refresh(entry)
    return entry


def test_dlq_drain_replays_recent_pipeline_task(db):
    """A recent DLQ entry for a known pipeline task should be redispatched."""
    lead_id = uuid.uuid4()
    entry = _make_dlq(
        db,
        task_name="app.workers.tasks.task_enrich_lead",
        lead_id=lead_id,
        pipeline_run_id=uuid.uuid4(),
    )

    with patch("app.workers.janitor.celery_app.send_task") as mock_send:
        from app.workers.janitor import drain_dead_letter_queue

        result = drain_dead_letter_queue(session_factory=lambda: db)

    assert result["replayed"] == 1
    assert result["skipped_unknown"] == 0
    mock_send.assert_called_once()
    args, kwargs = mock_send.call_args
    assert args[0] == "app.workers.tasks.task_enrich_lead"
    assert kwargs["args"] == [str(lead_id)]
    assert kwargs["kwargs"]["correlation_id"] == "corr-test"

    db.expire_all()
    refreshed = db.get(DeadLetterTask, entry.id)
    assert refreshed.replayed_at is not None


def test_dlq_drain_skips_unknown_task_name(db):
    """Unknown task names are not replayed but marked so we don't loop."""
    entry = _make_dlq(
        db,
        task_name="app.workers.mystery.task_nope",
        lead_id=uuid.uuid4(),
    )

    with patch("app.workers.janitor.celery_app.send_task") as mock_send:
        from app.workers.janitor import drain_dead_letter_queue

        result = drain_dead_letter_queue(session_factory=lambda: db)

    assert result["replayed"] == 0
    assert result["skipped_unknown"] == 1
    mock_send.assert_not_called()

    db.expire_all()
    refreshed = db.get(DeadLetterTask, entry.id)
    assert refreshed.replayed_at is not None


def test_dlq_drain_ignores_stale_entries(db):
    """DLQ entries older than 24h are NOT replayed (too risky, likely stale state)."""
    old_created = datetime.now(UTC) - timedelta(hours=48)
    entry = _make_dlq(
        db,
        task_name="app.workers.tasks.task_enrich_lead",
        lead_id=uuid.uuid4(),
        created_at=old_created,
    )

    with patch("app.workers.janitor.celery_app.send_task") as mock_send:
        from app.workers.janitor import drain_dead_letter_queue

        result = drain_dead_letter_queue(session_factory=lambda: db)

    assert result["replayed"] == 0
    assert result["inspected"] == 0
    mock_send.assert_not_called()

    db.expire_all()
    refreshed = db.get(DeadLetterTask, entry.id)
    assert refreshed.replayed_at is None


def test_dlq_drain_skips_entry_without_lead_id(db):
    """Known task with no lead_id -> cannot reconstruct args; mark and skip."""
    entry = _make_dlq(
        db,
        task_name="app.workers.tasks.task_enrich_lead",
        lead_id=None,
    )

    with patch("app.workers.janitor.celery_app.send_task") as mock_send:
        from app.workers.janitor import drain_dead_letter_queue

        result = drain_dead_letter_queue(session_factory=lambda: db)

    assert result["replayed"] == 0
    assert result["skipped_unknown"] == 1
    mock_send.assert_not_called()

    db.expire_all()
    refreshed = db.get(DeadLetterTask, entry.id)
    assert refreshed.replayed_at is not None


def test_dlq_drain_survives_send_task_exception(db):
    """If send_task raises, the entry is still marked replayed_at to prevent loops."""
    entry = _make_dlq(
        db,
        task_name="app.workers.tasks.task_enrich_lead",
        lead_id=uuid.uuid4(),
    )

    with patch(
        "app.workers.janitor.celery_app.send_task",
        side_effect=RuntimeError("broker offline"),
    ):
        from app.workers.janitor import drain_dead_letter_queue

        # Must not raise.
        result = drain_dead_letter_queue(session_factory=lambda: db)

    # replayed counter did NOT increment (dispatch failed), but entry is
    # marked to prevent infinite retry.
    assert result["replayed"] == 0
    # Failed dispatch is surfaced as its own counter so an all-hour broker
    # outage is visible in the structured log instead of silent.
    assert result["failed_dispatch"] == 1

    db.expire_all()
    refreshed = db.get(DeadLetterTask, entry.id)
    assert refreshed.replayed_at is not None


def test_dlq_drain_respects_batch_limit(db):
    """A single tick processes at most DLQ_REPLAY_BATCH_LIMIT entries."""
    from app.workers.janitor import DLQ_REPLAY_BATCH_LIMIT

    for _ in range(DLQ_REPLAY_BATCH_LIMIT + 5):
        _make_dlq(
            db,
            task_name="app.workers.tasks.task_enrich_lead",
            lead_id=uuid.uuid4(),
        )

    with patch("app.workers.janitor.celery_app.send_task"):
        from app.workers.janitor import drain_dead_letter_queue

        result = drain_dead_letter_queue(session_factory=lambda: db)

    assert result["inspected"] == DLQ_REPLAY_BATCH_LIMIT
    assert result["replayed"] == DLQ_REPLAY_BATCH_LIMIT
