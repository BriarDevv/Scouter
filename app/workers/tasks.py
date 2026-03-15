"""Celery tasks for async processing of leads."""

import json as _json
import uuid

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.llm.client import evaluate_lead_quality, summarize_business
from app.llm.roles import LLMRole
from app.models.inbound_mail import InboundMessage
from app.models.lead import Lead
from app.models.outreach import OutreachDraft
from app.services.enrichment_service import enrich_lead
from app.services.operational_settings_service import get_cached_settings
from app.services.outreach_service import generate_outreach_draft
from app.services.reply_draft_review_service import (
    mark_reply_assistant_review_failed,
    review_reply_assistant_draft_with_reviewer,
)
from app.services.review_service import (
    review_draft_with_reviewer,
    review_inbound_message_with_reviewer,
    review_lead_with_reviewer,
)
from app.services.scoring_service import score_lead
from app.services.task_tracking_service import (
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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_enrich_lead(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Async task: enrich a lead with website analysis and signals."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "enrichment")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
                current_step="enrichment",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_enrich_lead",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                correlation_id=correlation_id,
                current_step="enrichment",
            )

            lead = enrich_lead(db, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="enrichment",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "not_found", "lead_id": lead_id}

            result = {"status": "ok", "lead_id": lead_id, "signals": len(lead.signals)}
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="enrichment",
                pipeline_run_id=pipeline_uuid,
            )
            logger.info("task_step_completed", task_name="task_enrich_lead", result=result)
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_enrich_lead",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="enrichment",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def task_score_lead(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Async task: score a lead based on signals."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "scoring")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
                current_step="scoring",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_score_lead",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                correlation_id=correlation_id,
                current_step="scoring",
            )

            lead = score_lead(db, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="scoring",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "not_found", "lead_id": lead_id}

            result = {"status": "ok", "lead_id": lead_id, "score": lead.score}
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="scoring",
                pipeline_run_id=pipeline_uuid,
            )
            logger.info("task_step_completed", task_name="task_score_lead", result=result)
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_score_lead",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="scoring",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def task_analyze_lead(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Async task: run LLM analysis (summary + quality evaluation) on a lead."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "llm")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
                current_step="analysis",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_analyze_lead",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                correlation_id=correlation_id,
                current_step="analysis",
            )

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="analysis",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "not_found", "lead_id": lead_id}

            summary = summarize_business(
                business_name=lead.business_name,
                industry=lead.industry,
                city=lead.city,
                website_url=lead.website_url,
                instagram_url=lead.instagram_url,
                signals=list(lead.signals),
                role=LLMRole.EXECUTOR,
            )
            lead.llm_summary = summary

            evaluation = evaluate_lead_quality(
                business_name=lead.business_name,
                industry=lead.industry,
                city=lead.city,
                website_url=lead.website_url,
                instagram_url=lead.instagram_url,
                signals=list(lead.signals),
                score=lead.score,
                role=LLMRole.EXECUTOR,
            )
            lead.llm_quality_assessment = evaluation["reasoning"]
            lead.llm_suggested_angle = evaluation["suggested_angle"]

            db.commit()
            result = {
                "status": "ok",
                "lead_id": lead_id,
                "quality": evaluation["quality"],
            }
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="analysis",
                pipeline_run_id=pipeline_uuid,
            )
            logger.info("task_step_completed", task_name="task_analyze_lead", result=result)
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_analyze_lead",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="analysis",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def task_generate_draft(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Async task: generate outreach email draft."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "llm")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
                current_step="draft_generation",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_generate_draft",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                correlation_id=correlation_id,
                current_step="draft_generation",
            )

            draft = generate_outreach_draft(db, uuid.UUID(lead_id))
            if not draft:
                error = "Draft generation failed"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="draft_generation",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "failed", "lead_id": lead_id}

            result = {"status": "ok", "lead_id": lead_id, "draft_id": str(draft.id)}
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="draft_generation",
                pipeline_run_id=pipeline_uuid,
                pipeline_status="succeeded" if pipeline_uuid else None,
            )
            if pipeline_uuid:
                with SessionLocal() as pipeline_db:
                    from app.services.task_tracking_service import update_pipeline_run

                    update_pipeline_run(
                        pipeline_db,
                        pipeline_uuid,
                        current_step="completed",
                        status="succeeded",
                        result=result,
                        error=None,
                        finished=True,
                    )
            logger.info("task_step_completed", task_name="task_generate_draft", result=result)
            return result
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_generate_draft",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="draft_generation",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=90)
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
                result = {"status": "skipped", "reason": "reviewer_disabled", "lead_id": lead_id}
                mark_task_succeeded(db, task_id=task_id, result=result, current_step="lead_review")
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
            logger.info("task_step_completed", task_name="task_review_lead", result=result)
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
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=90)
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
                result = {"status": "skipped", "reason": "reviewer_disabled", "draft_id": draft_id}
                mark_task_succeeded(db, task_id=task_id, result=result, current_step="draft_review")
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
            logger.info("task_step_completed", task_name="task_review_draft", result=result)
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
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=90)
def task_review_inbound_message(self, message_id: str) -> dict:
    """Async task: run reviewer-only second opinion on an inbound reply."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    lead_id: str | None = None

    try:
        with SessionLocal() as db:
            message = db.get(InboundMessage, uuid.UUID(message_id))
            if not message:
                bind_tracking_context(task_id=task_id, current_step="inbound_reply_review")
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
                result = {"status": "skipped", "reason": "reviewer_disabled", "inbound_message_id": message_id}
                mark_task_succeeded(db, task_id=task_id, result=result, current_step="inbound_reply_review")
                return result

            payload = review_inbound_message_with_reviewer(db, uuid.UUID(message_id))
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
            logger.info("task_step_completed", task_name="task_review_inbound_message", result=result)
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
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=90)
def task_review_reply_assistant_draft(self, message_id: str) -> dict:
    """Async task: run reviewer-only second opinion on an assisted reply draft."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    lead_id: str | None = None

    try:
        with SessionLocal() as db:
            message = db.get(InboundMessage, uuid.UUID(message_id))
            if not message:
                bind_tracking_context(task_id=task_id, current_step="reply_draft_review")
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
                result = {"status": "skipped", "reason": "reviewer_disabled", "inbound_message_id": message_id}
                mark_task_succeeded(db, task_id=task_id, result=result, current_step="reply_draft_review")
                return result

            payload = review_reply_assistant_draft_with_reviewer(db, uuid.UUID(message_id))
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
        raise self.retry(exc=exc)
    finally:
        clear_tracking_context()


@celery_app.task(bind=True)
def task_full_pipeline(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Run the full pipeline: enrich -> score -> analyze -> generate draft."""
    from celery import chain

    task_id = str(self.request.id)
    queue = _queue_name(self.request, "default")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
                current_step="pipeline_dispatch",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_full_pipeline",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                correlation_id=correlation_id,
                current_step="pipeline_dispatch",
            )

            pipeline = chain(
                task_enrich_lead.si(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                ),
                task_score_lead.si(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                ),
                task_analyze_lead.si(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                ),
                task_generate_draft.si(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                ),
            )
            result = pipeline.apply_async()
            payload = {
                "status": "pipeline_started",
                "lead_id": lead_id,
                "pipeline_run_id": pipeline_run_id,
                "dispatched_task_id": str(result.id),
            }
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=payload,
                current_step="pipeline_dispatch",
                pipeline_run_id=pipeline_uuid,
                pipeline_status="running" if pipeline_uuid else None,
            )
            logger.info("pipeline_dispatched", result=payload)
            return payload
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_full_pipeline",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="pipeline_dispatch",
            queue=queue,
            error=str(exc),
        )
        raise
    finally:
        clear_tracking_context()


# ── Batch pipeline task ──────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.task_batch_pipeline", bind=True, max_retries=0)
def task_batch_pipeline(self, status_filter: str = "new"):
    """Process ALL leads with the given status through the full pipeline, one by one.

    Progress is tracked in Redis so the frontend can poll and the user can stop.
    """
    from app.services.enrichment_service import enrich_lead
    from app.services.scoring_service import score_lead
    from app.outreach.generator import generate_draft_content
    from redis import Redis
    from app.core.config import settings as env

    redis = Redis.from_url(env.REDIS_URL)
    redis_key = "pipeline:batch"
    task_id = str(self.request.id)

    db = SessionLocal()
    try:
        leads = db.query(Lead).filter(Lead.status == status_filter).order_by(Lead.created_at).all()
        total = len(leads)

        if total == 0:
            redis.set(redis_key, _json.dumps({
                "status": "done", "task_id": task_id,
                "total": 0, "processed": 0, "current_lead": None,
            }), ex=3600)
            return

        progress = {
            "status": "running",
            "task_id": task_id,
            "total": total,
            "processed": 0,
            "current_lead": None,
            "current_step": "",
            "errors": 0,
        }
        redis.set(redis_key, _json.dumps(progress), ex=3600)

        for idx, lead in enumerate(leads):
            # Check if stop was requested (Redis key deleted)
            current = redis.get(redis_key)
            if not current:
                logger.info("batch_pipeline_stopped_by_user")
                return
            cur_data = _json.loads(current)
            if cur_data.get("status") == "stopping":
                redis.set(redis_key, _json.dumps({
                    **progress, "status": "stopped",
                }), ex=3600)
                logger.info("batch_pipeline_stopped_by_user")
                return

            progress["current_lead"] = lead.business_name
            progress["processed"] = idx

            try:
                # Step 1: Enrich
                progress["current_step"] = "enrichment"
                redis.set(redis_key, _json.dumps(progress), ex=3600)
                enrich_lead(db, lead.id)

                # Step 2: Score
                progress["current_step"] = "scoring"
                redis.set(redis_key, _json.dumps(progress), ex=3600)
                score_lead(db, lead.id)

                # Step 3: LLM Analysis
                progress["current_step"] = "analysis"
                redis.set(redis_key, _json.dumps(progress), ex=3600)

                db.refresh(lead)
                from app.llm.client import summarize_business, evaluate_lead_quality
                from app.llm.roles import LLMRole as _LLMRole

                summary = summarize_business(
                    business_name=lead.business_name,
                    industry=lead.industry,
                    city=lead.city,
                    website_url=lead.website_url,
                    instagram_url=lead.instagram_url,
                    signals=list(lead.signals),
                    role=_LLMRole.EXECUTOR,
                )
                lead.llm_summary = summary

                evaluation = evaluate_lead_quality(
                    business_name=lead.business_name,
                    industry=lead.industry,
                    city=lead.city,
                    website_url=lead.website_url,
                    instagram_url=lead.instagram_url,
                    signals=list(lead.signals),
                    score=lead.score,
                    role=_LLMRole.EXECUTOR,
                )
                lead.llm_quality_assessment = evaluation["reasoning"]
                lead.llm_suggested_angle = evaluation["suggested_angle"]
                db.commit()

                # Step 4: Generate draft
                progress["current_step"] = "draft"
                redis.set(redis_key, _json.dumps(progress), ex=3600)
                generate_draft_content(lead, db=db)

                logger.info("batch_pipeline_lead_done", lead=lead.business_name, idx=idx + 1, total=total)

            except Exception as exc:
                progress["errors"] = progress.get("errors", 0) + 1
                logger.error("batch_pipeline_lead_error", lead=lead.business_name, error=str(exc))

        progress["status"] = "done"
        progress["processed"] = total
        progress["current_lead"] = None
        progress["current_step"] = ""
        redis.set(redis_key, _json.dumps(progress), ex=3600)
        logger.info("batch_pipeline_done", total=total, errors=progress.get("errors", 0))

    except Exception as exc:
        redis.set(redis_key, _json.dumps({
            "status": "error", "task_id": task_id, "error": str(exc),
        }), ex=3600)
        logger.error("batch_pipeline_error", error=str(exc))
    finally:
        db.close()


# ── Google Maps crawl task ────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.task_crawl_territory", bind=True, max_retries=0)
def task_crawl_territory(
    self,
    territory_id: str,
    categories: list[str] | None = None,
    only_without_website: bool = False,
    max_results_per_category: int = 20,
    target_leads: int = 50,
):
    """Crawl Google Maps for all cities in a territory."""
    from app.crawlers.google_maps_crawler import GoogleMapsCrawler
    from app.models.territory import Territory
    from app.models.lead_source import LeadSource, SourceType
    from app.schemas.lead import LeadCreate
    from app.services.lead_service import _compute_dedup_hash, create_lead
    from redis import Redis
    from app.core.config import settings as env

    redis = Redis.from_url(env.REDIS_URL)
    redis_key = f"crawl:territory:{territory_id}"

    db = SessionLocal()
    try:
        territory = db.get(Territory, uuid.UUID(territory_id))
        if not territory:
            redis.set(redis_key, _json.dumps({"status": "error", "error": "Territorio no encontrado"}), ex=3600)
            return

        cities = territory.cities or []
        if not cities:
            redis.set(redis_key, _json.dumps({"status": "error", "error": "El territorio no tiene ciudades"}), ex=3600)
            return

        # Get or create source
        source = db.query(LeadSource).filter(LeadSource.name == "google_maps").first()
        if not source:
            source = LeadSource(name="google_maps", source_type=SourceType.CRAWLER, description="Google Maps Places API")
            db.add(source)
            db.commit()
            db.refresh(source)

        crawler = GoogleMapsCrawler()
        total_found = 0
        total_created = 0
        total_dup = 0
        task_id = str(self.request.id)

        progress = {
            "status": "running",
            "task_id": task_id,
            "territory": territory.name,
            "total_cities": len(cities),
            "current_city_idx": 0,
            "current_city": "",
            "leads_found": 0,
            "leads_created": 0,
            "leads_skipped": 0,
        }
        redis.set(redis_key, _json.dumps(progress), ex=3600)

        for idx, city in enumerate(cities):
            progress["current_city_idx"] = idx + 1
            progress["current_city"] = city
            redis.set(redis_key, _json.dumps(progress), ex=3600)

            try:
                raw_leads = crawler.crawl(
                    city=city,
                    categories=categories,
                    max_results_per_category=max_results_per_category,
                    only_without_website=only_without_website,
                    target_leads=target_leads,
                )
            except Exception as exc:
                logger.error("crawl_city_error", city=city, error=str(exc))
                continue

            total_found += len(raw_leads)

            for raw in raw_leads:
                try:
                    dedup = _compute_dedup_hash(raw.business_name, raw.city, raw.website_url)
                    existing = db.execute(
                        select(Lead).where(Lead.dedup_hash == dedup)
                    ).scalar_one_or_none()
                    if existing:
                        total_dup += 1
                        continue

                    lead_data = LeadCreate(
                        business_name=raw.business_name,
                        industry=raw.industry,
                        city=raw.city,
                        zone=raw.zone,
                        website_url=raw.website_url,
                        instagram_url=raw.instagram_url,
                        phone=raw.phone,
                        source_id=source.id,
                        address=raw.address,
                        google_maps_url=raw.google_maps_url,
                        rating=raw.rating,
                        review_count=raw.review_count,
                        business_status=raw.business_status,
                        opening_hours=raw.opening_hours,
                        latitude=raw.latitude,
                        longitude=raw.longitude,
                    )
                    create_lead(db, lead_data)
                    total_created += 1
                except Exception:
                    total_dup += 1

            progress["leads_found"] = total_found
            progress["leads_created"] = total_created
            progress["leads_skipped"] = total_dup
            redis.set(redis_key, _json.dumps(progress), ex=3600)

        progress["status"] = "done"
        redis.set(redis_key, _json.dumps(progress), ex=3600)

        logger.info(
            "territory_crawl_done",
            territory=territory.name,
            cities=len(cities),
            found=total_found,
            created=total_created,
            skipped=total_dup,
        )
    except Exception as exc:
        redis.set(redis_key, _json.dumps({"status": "error", "error": str(exc)}), ex=3600)
        logger.error("territory_crawl_error", territory_id=territory_id, error=str(exc))
    finally:
        db.close()
