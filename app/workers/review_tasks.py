"""Celery tasks for reviewer-model second opinions."""

import uuid

from fastapi.encoders import jsonable_encoder

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.inbound_mail import InboundMessage
from app.models.outreach import OutreachDraft
from app.services.settings.operational_settings_service import get_cached_settings
from app.services.inbox.reply_draft_review_service import (
    mark_reply_assistant_review_failed,
    review_reply_assistant_draft_with_reviewer,
)
from app.services.review_service import (
    review_draft_with_reviewer,
    review_inbound_message_with_reviewer,
    review_lead_with_reviewer,
)
from app.services.pipeline.task_tracking_service import (
    bind_tracking_context,
    clear_tracking_context,
    mark_task_failed,
    mark_task_retrying,
    mark_task_running,
    mark_task_succeeded,
)
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def _queue_name(request, fallback: str) -> str:
    delivery_info = getattr(request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or delivery_info.get("queue") or fallback


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
        else:
            mark_task_retrying(
                db,
                task_id=task_id,
                error=error,
                current_step=current_step,
                pipeline_run_id=pipeline_run_id,
            )
        logger.error("task_step_failed", task_name=task_name, error=error)
        clear_tracking_context()


@celery_app.task(
    name="app.workers.tasks.task_review_lead",
    bind=True,
    max_retries=1,
    default_retry_delay=90,
)
def task_review_lead(self, lead_id: str) -> dict:
    """Async task: run reviewer-only second opinion on a lead."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                current_step="lead_review",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_review_lead",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                current_step="lead_review",
            )

            ops = get_cached_settings(db)
            if not ops.reviewer_enabled:
                result = {
                    "status": "skipped",
                    "reason": "reviewer_disabled",
                    "lead_id": lead_id,
                }
                mark_task_succeeded(
                    db, task_id=task_id, result=result, current_step="lead_review"
                )
                return result

            payload = review_lead_with_reviewer(db, uuid.UUID(lead_id))
            if not payload:
                error = "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="lead_review",
                )
                return {"status": "not_found", "lead_id": lead_id}

            result = {
                "status": "ok",
                "lead_id": lead_id,
                **payload,
            }
            result = jsonable_encoder(result)
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="lead_review",
            )
            logger.info(
                "task_step_completed", task_name="task_review_lead", result=result
            )
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_review_lead",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=None,
            correlation_id=None,
            current_step="lead_review",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()


@celery_app.task(
    name="app.workers.tasks.task_review_draft",
    bind=True,
    max_retries=1,
    default_retry_delay=90,
)
def task_review_draft(self, draft_id: str) -> dict:
    """Async task: run reviewer-only second opinion on a draft."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    lead_id: str | None = None

    try:
        with SessionLocal() as db:
            draft = db.get(OutreachDraft, uuid.UUID(draft_id))
            if not draft or not draft.lead_id:
                bind_tracking_context(task_id=task_id, current_step="draft_review")
                mark_task_running(
                    db,
                    task_id=task_id,
                    task_name="task_review_draft",
                    queue=queue,
                    current_step="draft_review",
                )
                error = "Draft not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="draft_review",
                )
                return {"status": "not_found", "draft_id": draft_id}

            lead_id = str(draft.lead_id)
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                current_step="draft_review",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_review_draft",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                current_step="draft_review",
            )

            ops = get_cached_settings(db)
            if not ops.reviewer_enabled:
                result = {
                    "status": "skipped",
                    "reason": "reviewer_disabled",
                    "draft_id": draft_id,
                }
                mark_task_succeeded(
                    db, task_id=task_id, result=result, current_step="draft_review"
                )
                return result

            draft_payload = review_draft_with_reviewer(db, uuid.UUID(draft_id))
            if not draft_payload:
                error = "Draft not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="draft_review",
                )
                return {"status": "not_found", "draft_id": draft_id}

            result = {
                "status": "ok",
                "draft_id": draft_id,
                **draft_payload,
            }
            result = jsonable_encoder(result)
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="draft_review",
            )
            logger.info(
                "task_step_completed", task_name="task_review_draft", result=result
            )
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_review_draft",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=None,
            correlation_id=None,
            current_step="draft_review",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()


@celery_app.task(
    name="app.workers.tasks.task_review_inbound_message",
    bind=True,
    max_retries=1,
    default_retry_delay=90,
)
def task_review_inbound_message(self, message_id: str) -> dict:
    """Async task: run reviewer-only second opinion on an inbound reply."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    lead_id: str | None = None

    try:
        with SessionLocal() as db:
            message = db.get(InboundMessage, uuid.UUID(message_id))
            if not message:
                bind_tracking_context(
                    task_id=task_id, current_step="inbound_reply_review"
                )
                mark_task_running(
                    db,
                    task_id=task_id,
                    task_name="task_review_inbound_message",
                    queue=queue,
                    current_step="inbound_reply_review",
                )
                error = "Inbound message not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="inbound_reply_review",
                )
                return {"status": "not_found", "inbound_message_id": message_id}

            lead_id = str(message.lead_id) if message.lead_id else None
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                current_step="inbound_reply_review",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_review_inbound_message",
                queue=queue,
                lead_id=uuid.UUID(lead_id) if lead_id else None,
                current_step="inbound_reply_review",
            )

            ops = get_cached_settings(db)
            if not ops.reviewer_enabled:
                result = {
                    "status": "skipped",
                    "reason": "reviewer_disabled",
                    "inbound_message_id": message_id,
                }
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="inbound_reply_review",
                )
                return result

            payload = review_inbound_message_with_reviewer(
                db, uuid.UUID(message_id)
            )
            if not payload:
                error = "Inbound message not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="inbound_reply_review",
                )
                return {"status": "not_found", "inbound_message_id": message_id}

            result = {
                "status": "ok",
                "inbound_message_id": message_id,
                **payload,
            }
            result = jsonable_encoder(result)
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="inbound_reply_review",
            )
            logger.info(
                "task_step_completed",
                task_name="task_review_inbound_message",
                result=result,
            )
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_review_inbound_message",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=None,
            correlation_id=None,
            current_step="inbound_reply_review",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()


@celery_app.task(
    name="app.workers.tasks.task_review_reply_assistant_draft",
    bind=True,
    max_retries=1,
    default_retry_delay=90,
)
def task_review_reply_assistant_draft(self, message_id: str) -> dict:
    """Async task: run reviewer-only second opinion on an assisted reply draft."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    lead_id: str | None = None

    try:
        with SessionLocal() as db:
            message = db.get(InboundMessage, uuid.UUID(message_id))
            if not message:
                bind_tracking_context(
                    task_id=task_id, current_step="reply_draft_review"
                )
                mark_task_running(
                    db,
                    task_id=task_id,
                    task_name="task_review_reply_assistant_draft",
                    queue=queue,
                    current_step="reply_draft_review",
                )
                error = "Inbound message not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="reply_draft_review",
                )
                return {"status": "not_found", "inbound_message_id": message_id}

            lead_id = str(message.lead_id) if message.lead_id else None
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                current_step="reply_draft_review",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_review_reply_assistant_draft",
                queue=queue,
                lead_id=uuid.UUID(lead_id) if lead_id else None,
                current_step="reply_draft_review",
            )

            ops = get_cached_settings(db)
            if not ops.reviewer_enabled:
                result = {
                    "status": "skipped",
                    "reason": "reviewer_disabled",
                    "inbound_message_id": message_id,
                }
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="reply_draft_review",
                )
                return result

            payload = review_reply_assistant_draft_with_reviewer(
                db, uuid.UUID(message_id)
            )
            if not payload:
                error = "Reply assistant draft not found"
                mark_reply_assistant_review_failed(
                    db,
                    uuid.UUID(message_id),
                    error=error,
                    task_id=task_id,
                )
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="reply_draft_review",
                )
                return {"status": "not_found", "inbound_message_id": message_id}

            result = {
                "status": "ok",
                "inbound_message_id": message_id,
                **payload,
            }
            result = jsonable_encoder(result)
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="reply_draft_review",
            )
            logger.info(
                "task_step_completed",
                task_name="task_review_reply_assistant_draft",
                result=result,
            )
            return result
    except Exception as exc:
        with SessionLocal() as failure_db:
            mark_reply_assistant_review_failed(
                failure_db,
                uuid.UUID(message_id),
                error=str(exc),
                task_id=task_id,
            )
        _track_failure(
            task=self,
            task_name="task_review_reply_assistant_draft",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=None,
            correlation_id=None,
            current_step="reply_draft_review",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()
