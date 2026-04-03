"""Celery tasks for batch operations."""

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.lead import Lead
from app.services.operational_task_service import (
    BATCH_PIPELINE_SCOPE_KEY,
    RESCORE_ALL_REDIS_KEY,
    RESCORE_ALL_SCOPE_KEY,
    build_rescore_all_status_payload,
    mirror_rescore_all_state,
    persist_rescore_all_state,
    should_stop_operational_task,
)
from app.services.scoring_service import score_lead
from app.services.task_tracking_service import (
    bind_tracking_context,
    clear_tracking_context,
    mark_task_running,
)
from app.workers.celery_app import celery_app
from app.workflows.batch_pipeline import run_batch_pipeline_workflow

logger = get_logger(__name__)


def _queue_name(request, fallback: str) -> str:
    delivery_info = getattr(request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or delivery_info.get("queue") or fallback


def _request_task_id(request) -> str:
    request_id = getattr(request, "id", None)
    return str(request_id or uuid.uuid4())


# ── Batch pipeline task ──────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.task_batch_pipeline",
    bind=True,
    max_retries=0,
    soft_time_limit=7200,
    time_limit=7500,
)
def task_batch_pipeline(
    self, status_filter: str = "new", correlation_id: str | None = None
):
    """Thin Celery wrapper around the batch pipeline workflow."""
    task_id = _request_task_id(self.request)
    queue = _queue_name(self.request, "default")

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                task_id=task_id,
                correlation_id=correlation_id,
                current_step="batch_dispatch",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_batch_pipeline",
                queue=queue,
                correlation_id=correlation_id,
                scope_key=BATCH_PIPELINE_SCOPE_KEY,
                current_step="batch_dispatch",
            )
        return run_batch_pipeline_workflow(
            task_id=task_id,
            status_filter=status_filter,
            correlation_id=correlation_id,
        )
    finally:
        clear_tracking_context()


# ── Re-score task ─────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.task_rescore_all",
    bind=True,
    max_retries=0,
    soft_time_limit=3600,
    time_limit=3900,
)
def task_rescore_all(self, correlation_id: str | None = None):
    """Re-score all leads. Useful after scoring weight changes."""
    task_id = _request_task_id(self.request)
    queue = _queue_name(self.request, "default")
    current_step = "rescore_dispatch"
    total = 0
    rescored = 0
    errors = 0

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                task_id=task_id,
                correlation_id=correlation_id,
                current_step=current_step,
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_rescore_all",
                queue=queue,
                correlation_id=correlation_id,
                scope_key=RESCORE_ALL_SCOPE_KEY,
                current_step=current_step,
            )
            lead_ids = [
                row
                for (row,) in db.query(Lead.id).filter(Lead.score.isnot(None)).all()
            ]

        total = len(lead_ids)
        persist_rescore_all_state(
            task_id,
            current_step=current_step,
            total=total,
            rescored=rescored,
            errors=errors,
            clear_error=True,
        )
        mirror_rescore_all_state(
            build_rescore_all_status_payload(
                status="running",
                task_id=task_id,
                total=total,
                rescored=rescored,
                errors=errors,
                current_step=current_step,
            )
        )

        for lead_id in lead_ids:
            current_step = "rescore_scoring"
            persist_rescore_all_state(
                task_id,
                current_step=current_step,
                total=total,
                rescored=rescored,
                errors=errors,
                current_lead_id=str(lead_id),
            )

            if should_stop_operational_task(
                task_id=task_id,
                redis_key=RESCORE_ALL_REDIS_KEY,
            ):
                current_step = "rescore_stopped"
                persist_rescore_all_state(
                    task_id,
                    current_step=current_step,
                    total=total,
                    rescored=rescored,
                    errors=errors,
                    status="stopped",
                    finished=True,
                )
                mirror_rescore_all_state(
                    build_rescore_all_status_payload(
                        status="stopped",
                        task_id=task_id,
                        total=total,
                        rescored=rescored,
                        errors=errors,
                        current_step=current_step,
                    )
                )
                logger.info("rescore_all_stopped_by_user")
                return {"status": "stopped", "task_id": task_id}

            try:
                with SessionLocal() as db:
                    score_lead(db, lead_id)
                rescored += 1
            except Exception as exc:
                errors += 1
                logger.error(
                    "rescore_lead_error", lead_id=str(lead_id), error=str(exc)
                )
            persist_rescore_all_state(
                task_id,
                current_step=current_step,
                total=total,
                rescored=rescored,
                errors=errors,
            )

            processed_count = rescored + errors
            if processed_count % 20 == 0 or processed_count == total:
                mirror_rescore_all_state(
                    build_rescore_all_status_payload(
                        status="running",
                        task_id=task_id,
                        total=total,
                        rescored=rescored,
                        errors=errors,
                        current_step=current_step,
                    )
                )

        current_step = "rescore_completed"
        result = {
            "status": "done",
            "task_id": task_id,
            "total": total,
            "rescored": rescored,
            "errors": errors,
        }
        persist_rescore_all_state(
            task_id,
            current_step=current_step,
            total=total,
            rescored=rescored,
            errors=errors,
            status="succeeded",
            clear_error=True,
            finished=True,
            result=result,
            stop_requested=False,
        )
        mirror_rescore_all_state(
            build_rescore_all_status_payload(
                status="done",
                task_id=task_id,
                total=total,
                rescored=rescored,
                errors=errors,
                current_step=current_step,
            )
        )
        logger.info(
            "rescore_all_done", total=total, rescored=rescored, errors=errors
        )
        return result
    except Exception as exc:
        persist_rescore_all_state(
            task_id,
            current_step=current_step,
            total=total,
            rescored=rescored,
            errors=errors,
            status="failed",
            error=str(exc),
            finished=True,
        )
        mirror_rescore_all_state(
            build_rescore_all_status_payload(
                status="error",
                task_id=task_id,
                total=total,
                rescored=rescored,
                errors=errors,
                current_step=current_step,
                error=str(exc),
            )
        )
        logger.error("rescore_all_error", error=str(exc))
        raise
    finally:
        clear_tracking_context()
