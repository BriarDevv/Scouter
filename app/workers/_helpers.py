"""Shared worker helper functions used across pipeline, research, and review tasks."""

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.notifications.notification_emitter import on_repeated_failures
from app.services.pipeline.task_tracking_service import (
    bind_tracking_context,
    clear_tracking_context,
    mark_task_failed,
    mark_task_retrying,
    mark_task_running,
)

logger = get_logger(__name__)


def _queue_name(request, fallback: str) -> str:
    delivery_info = getattr(request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or delivery_info.get("queue") or fallback


def _pipeline_uuid(pipeline_run_id: str | None) -> uuid.UUID | None:
    return uuid.UUID(pipeline_run_id) if pipeline_run_id else None


def _track_failure(
    *,
    task,
    task_name: str,
    task_id: str,
    lead_id: str | None,
    pipeline_run_id: uuid.UUID | None,
    correlation_id: str | None,
    current_step: str,
    queue: str,
    error: str,
) -> None:
    with SessionLocal() as db:
        bind_tracking_context(
            lead_id=lead_id,
            task_id=task_id,
            pipeline_run_id=str(pipeline_run_id) if pipeline_run_id else None,
            correlation_id=correlation_id,
            current_step=current_step,
        )
        mark_task_running(
            db,
            task_id=task_id,
            task_name=task_name,
            queue=queue,
            lead_id=uuid.UUID(lead_id) if lead_id else None,
            pipeline_run_id=pipeline_run_id,
            correlation_id=correlation_id,
            current_step=current_step,
        )
        if task.request.retries >= task.max_retries:
            mark_task_failed(
                db,
                task_id=task_id,
                error=error,
                current_step=current_step,
                pipeline_run_id=pipeline_run_id,
            )
            on_repeated_failures(
                db,
                failure_type=task_name,
                count=task.max_retries + 1,
                detail=f"Task exhausted all retries. Step: {current_step}. Error: {error[:200]}",
            )
            # Insert dead letter record for permanently failed tasks
            try:
                from app.models.dead_letter import DeadLetterTask

                dead_letter = DeadLetterTask(
                    task_name=task_name,
                    lead_id=uuid.UUID(lead_id) if lead_id else None,
                    pipeline_run_id=pipeline_run_id,
                    step=current_step,
                    error=error[:2000] if error else None,
                    payload={
                        "task_id": task_id,
                        "correlation_id": correlation_id,
                        "queue": queue,
                        "max_retries": task.max_retries,
                    },
                )
                db.add(dead_letter)
            except Exception:
                logger.warning("dead_letter_insert_failed", task_id=task_id)
        else:
            mark_task_retrying(
                db,
                task_id=task_id,
                error=error,
                current_step=current_step,
                pipeline_run_id=pipeline_run_id,
            )
        db.commit()
        logger.error("task_step_failed", task_name=task_name, error=error)
        clear_tracking_context()
