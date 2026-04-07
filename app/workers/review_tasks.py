"""Celery tasks for reviewer-model second opinions."""

import uuid

from fastapi.encoders import jsonable_encoder

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.inbound_mail import InboundMessage
from app.models.outreach import OutreachDraft
from app.services.inbox.reply_draft_review_service import (
    mark_reply_assistant_review_failed,
    review_reply_assistant_draft_with_reviewer,
)
from app.services.pipeline.task_tracking_service import (
    tracked_task_step,
)
from app.services.review_service import (
    review_draft_with_reviewer,
    review_inbound_message_with_reviewer,
    review_lead_with_reviewer,
)
from app.services.settings.operational_settings_service import get_cached_settings
from app.workers._helpers import _queue_name, _track_failure
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_review_lead",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            current_step="lead_review",
        ) as tracker:

            ops = get_cached_settings(db)
            if not ops.reviewer_enabled:
                result = {
                    "status": "skipped",
                    "reason": "reviewer_disabled",
                    "lead_id": lead_id,
                }
                tracker.succeed(result)
                return result

            payload = review_lead_with_reviewer(db, uuid.UUID(lead_id))
            if not payload:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            result = {
                "status": "ok",
                "lead_id": lead_id,
                **payload,
            }
            result = jsonable_encoder(result)
            tracker.succeed(result)
            db.commit()
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
            lead_id = str(draft.lead_id) if draft and draft.lead_id else None
            with tracked_task_step(
                db,
                task_id=task_id,
                task_name="task_review_draft",
                queue=queue,
                lead_id=uuid.UUID(lead_id) if lead_id else None,
                current_step="draft_review",
            ) as tracker:
                if not draft or not draft.lead_id:
                    error = "Draft not found"
                    tracker.fail(error)
                    return {"status": "not_found", "draft_id": draft_id}

                ops = get_cached_settings(db)
                if not ops.reviewer_enabled:
                    result = {
                        "status": "skipped",
                        "reason": "reviewer_disabled",
                        "draft_id": draft_id,
                    }
                    tracker.succeed(result)
                    return result

                draft_payload = review_draft_with_reviewer(db, uuid.UUID(draft_id))
                if not draft_payload:
                    error = "Draft not found"
                    tracker.fail(error)
                    return {"status": "not_found", "draft_id": draft_id}

                result = {
                    "status": "ok",
                    "draft_id": draft_id,
                    **draft_payload,
                }
                result = jsonable_encoder(result)
                tracker.succeed(result)
                db.commit()
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
                return {"status": "not_found", "inbound_message_id": message_id}
            lead_id = str(message.lead_id) if message.lead_id else None
            with tracked_task_step(
                db,
                task_id=task_id,
                task_name="task_review_inbound_message",
                queue=queue,
                lead_id=uuid.UUID(lead_id) if lead_id else None,
                correlation_id=None,
                current_step="inbound_reply_review",
            ) as tracker:
                ops = get_cached_settings(db)
                if not ops.reviewer_enabled:
                    result = {
                        "status": "skipped",
                        "reason": "reviewer_disabled",
                        "inbound_message_id": message_id,
                    }
                    tracker.succeed(result)
                    return result

                payload = review_inbound_message_with_reviewer(
                    db, uuid.UUID(message_id)
                )
                if not payload:
                    error = "Inbound message not found"
                    tracker.fail(error)
                    return {"status": "not_found", "inbound_message_id": message_id}

                result = {
                    "status": "ok",
                    "inbound_message_id": message_id,
                    **payload,
                }
                result = jsonable_encoder(result)
                tracker.succeed(result)
                db.commit()
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
            lead_id = str(message.lead_id) if message and message.lead_id else None
            with tracked_task_step(
                db,
                task_id=task_id,
                task_name="task_review_reply_assistant_draft",
                queue=queue,
                lead_id=uuid.UUID(lead_id) if lead_id else None,
                correlation_id=None,
                current_step="reply_draft_review",
            ) as tracker:
                if not message:
                    error = "Inbound message not found"
                    tracker.fail(error)
                    return {"status": "not_found", "inbound_message_id": message_id}

                ops = get_cached_settings(db)
                if not ops.reviewer_enabled:
                    result = {
                        "status": "skipped",
                        "reason": "reviewer_disabled",
                        "inbound_message_id": message_id,
                    }
                    tracker.succeed(result)
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
                    tracker.fail(error)
                    return {"status": "not_found", "inbound_message_id": message_id}

                result = {
                    "status": "ok",
                    "inbound_message_id": message_id,
                    **payload,
                }
                result = jsonable_encoder(result)
                tracker.succeed(result)
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
