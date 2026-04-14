"""Dead Letter Queue drain — hourly replay of failed pipeline tasks.

DLQ entries are written by app.workers._helpers._track_failure when a
pipeline task exhausts its retries. Without this drain they pile up as
a morgue. See docs/audits/repo-deep-audit.md section 6.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

# Task names we know how to replay automatically. Each accepts (lead_id)
# positionally + pipeline_run_id/correlation_id as kwargs.
_REPLAYABLE_PIPELINE_TASKS = frozenset(
    {
        "app.workers.tasks.task_enrich_lead",
        "app.workers.tasks.task_score_lead",
        "app.workers.tasks.task_analyze_lead",
        "app.workers.tasks.task_research_lead",
        "app.workers.tasks.task_generate_draft",
        "app.workers.brief_tasks.task_generate_brief",
        "app.workers.brief_tasks.task_review_brief",
    }
)

DLQ_REPLAY_WINDOW_HOURS = 24
DLQ_REPLAY_BATCH_LIMIT = 10


def drain_dead_letter_queue(session_factory=None) -> dict:
    """Replay pending DeadLetterTask entries created within the last 24h.

    Behavior:
    - Only replays task names in _REPLAYABLE_PIPELINE_TASKS. Unknown task
      names are marked replayed_at with a log warning so we don't loop on them.
    - Sets replayed_at BEFORE dispatch so a crash between mark and send
      won't double-send (worst case: one lost replay, never repeated).
    - Batches at DLQ_REPLAY_BATCH_LIMIT per tick to avoid flooding the
      broker on catastrophic backlog.
    """
    from app.models.dead_letter import DeadLetterTask

    cutoff = datetime.now(UTC) - timedelta(hours=DLQ_REPLAY_WINDOW_HOURS)
    factory = session_factory or SessionLocal
    replayed = 0
    skipped_unknown = 0
    failed_dispatch = 0

    with factory() as db:
        entries = (
            db.execute(
                select(DeadLetterTask)
                .where(
                    DeadLetterTask.replayed_at.is_(None),
                    DeadLetterTask.created_at >= cutoff,
                )
                .limit(DLQ_REPLAY_BATCH_LIMIT)
            )
            .scalars()
            .all()
        )

        for entry in entries:
            entry.replayed_at = datetime.now(UTC)

            if entry.task_name not in _REPLAYABLE_PIPELINE_TASKS:
                skipped_unknown += 1
                logger.warning(
                    "dlq_replay_unknown_task",
                    dlq_id=str(entry.id),
                    task_name=entry.task_name,
                )
                continue

            if entry.lead_id is None:
                skipped_unknown += 1
                logger.warning(
                    "dlq_replay_missing_lead_id",
                    dlq_id=str(entry.id),
                    task_name=entry.task_name,
                )
                continue

            payload = entry.payload or {}
            kwargs = {
                "pipeline_run_id": str(entry.pipeline_run_id) if entry.pipeline_run_id else None,
                "correlation_id": payload.get("correlation_id"),
            }
            try:
                celery_app.send_task(entry.task_name, args=[str(entry.lead_id)], kwargs=kwargs)
                replayed += 1
                logger.info(
                    "dlq_replay_dispatched",
                    dlq_id=str(entry.id),
                    task_name=entry.task_name,
                    lead_id=str(entry.lead_id),
                )
            except Exception as exc:
                failed_dispatch += 1
                logger.error(
                    "dlq_replay_dispatch_failed",
                    dlq_id=str(entry.id),
                    task_name=entry.task_name,
                    error=str(exc),
                )

        db.commit()

    result = {
        "replayed": replayed,
        "skipped_unknown": skipped_unknown,
        "failed_dispatch": failed_dispatch,
        "inspected": len(entries),
    }
    logger.info("dlq_drain_done", **result)
    return result
