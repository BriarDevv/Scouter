"""Celery tasks for async processing of leads."""

import json as _json
import uuid

from celery.exceptions import SoftTimeLimitExceeded
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
from app.services.operational_task_service import (
    BATCH_PIPELINE_REDIS_KEY,
    BATCH_PIPELINE_SCOPE_KEY,
    RESCORE_ALL_REDIS_KEY,
    RESCORE_ALL_SCOPE_KEY,
    build_batch_pipeline_progress,
    build_rescore_all_progress,
    build_territory_crawl_progress,
    mirror_batch_pipeline_state,
    mirror_legacy_operational_state,
    mirror_territory_crawl_state,
    persist_operational_task_state,
    should_stop_operational_task,
    territory_crawl_redis_key,
)
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
    is_task_stop_requested,
    mark_task_failed,
    mark_task_retrying,
    mark_task_running,
    mark_task_succeeded,
    update_task_run,
)
from app.workers.celery_app import celery_app
from app.workflows.outreach_draft_generation import (
    run_outreach_draft_automation,
    run_outreach_draft_generation_workflow,
    should_generate_outreach_email_draft,
)

logger = get_logger(__name__)


def _should_generate_draft(lead: Lead) -> bool:
    return should_generate_outreach_email_draft(lead)


def _queue_name(request, fallback: str) -> str:
    delivery_info = getattr(request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or delivery_info.get("queue") or fallback


def _pipeline_uuid(pipeline_run_id: str | None) -> uuid.UUID | None:
    return uuid.UUID(pipeline_run_id) if pipeline_run_id else None


def _request_task_id(request) -> str:
    request_id = getattr(request, "id", None)
    return str(request_id or uuid.uuid4())


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
    task_id = _request_task_id(self.request)
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

            lead = db.get(Lead, uuid.UUID(lead_id))
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

            # Idempotency guard: skip if already enriched (unless force)
            if lead.enriched_at is not None:
                result = {"status": "skipped", "lead_id": lead_id, "reason": "already_enriched"}
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="enrichment",
                    pipeline_run_id=pipeline_uuid,
                )
                logger.info("task_skipped_idempotent", task_name="task_enrich_lead", lead_id=lead_id)
                return result

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

            # Chain to scoring
            if pipeline_run_id:
                task_score_lead.delay(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                )

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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
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
    task_id = _request_task_id(self.request)
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

            lead = db.get(Lead, uuid.UUID(lead_id))
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

            # Idempotency guard: skip if already scored
            if lead.scored_at is not None:
                result = {"status": "skipped", "lead_id": lead_id, "reason": "already_scored", "score": lead.score}
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="scoring",
                    pipeline_run_id=pipeline_uuid,
                )
                logger.info("task_skipped_idempotent", task_name="task_score_lead", lead_id=lead_id)
                return result

            lead = score_lead(db, uuid.UUID(lead_id))
            if not lead:
                error = "Score failed"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="scoring",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "failed", "lead_id": lead_id}

            result = {"status": "ok", "lead_id": lead_id, "score": lead.score}
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="scoring",
                pipeline_run_id=pipeline_uuid,
            )
            logger.info("task_step_completed", task_name="task_score_lead", result=result)

            # Chain to analysis
            if pipeline_run_id:
                task_analyze_lead.delay(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                )

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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, soft_time_limit=300, time_limit=360)
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

            # Idempotency guard: skip if already analyzed
            if lead.llm_summary is not None:
                result = {
                    "status": "skipped",
                    "lead_id": lead_id,
                    "reason": "already_analyzed",
                    "quality": lead.llm_quality,
                }
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="analysis",
                    pipeline_run_id=pipeline_uuid,
                )
                logger.info("task_skipped_idempotent", task_name="task_analyze_lead", lead_id=lead_id)
                return result

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
            raw_quality = evaluation.get("quality", "unknown").lower().strip()
            if raw_quality not in ("high", "medium", "low"):
                logger.warning("quality_normalized_to_unknown", lead=lead.business_name, raw_quality=raw_quality)
            lead.llm_quality = raw_quality if raw_quality in ("high", "medium", "low") else "unknown"

            db.commit()
            result = {
                "status": "ok",
                "lead_id": lead_id,
                "quality": lead.llm_quality,
            }
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="analysis",
                pipeline_run_id=pipeline_uuid,
            )
            logger.info("task_step_completed", task_name="task_analyze_lead", result=result)

            # Chain next step based on quality
            if lead.llm_quality == "high":
                try:
                    task_research_lead.delay(
                        lead_id, pipeline_run_id, correlation_id,
                    )
                    logger.info(
                        "research_chained",
                        lead_id=lead_id,
                        quality=lead.llm_quality,
                    )
                except Exception as chain_exc:
                    logger.warning(
                        "research_chain_failed",
                        lead_id=lead_id,
                        error=str(chain_exc),
                    )
            elif pipeline_run_id:
                # Non-HIGH: chain directly to draft generation
                task_generate_draft.delay(
                    lead_id,
                    pipeline_run_id=pipeline_run_id,
                    correlation_id=correlation_id,
                )

            return result
    except SoftTimeLimitExceeded:
        logger.error("task_soft_time_limit", task_name="task_analyze_lead", task_id=task_id)
        with SessionLocal() as db:
            mark_task_failed(
                db,
                task_id=task_id,
                error="Soft time limit exceeded (5min)",
                current_step="analysis",
                pipeline_run_id=pipeline_uuid,
            )
        raise
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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, soft_time_limit=300, time_limit=360)
def task_generate_draft(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Async task: generate outreach email draft (only for high-quality leads)."""
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

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="draft_generation",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "not_found", "lead_id": lead_id}

            workflow_result = run_outreach_draft_generation_workflow(
                db,
                uuid.UUID(lead_id),
            )
            result = workflow_result.to_payload()

            if workflow_result.status == "not_found":
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error="Lead not found",
                    current_step="draft_generation",
                    pipeline_run_id=pipeline_uuid,
                )
                return result

            if workflow_result.status == "failed":
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=str(workflow_result.reason or "Draft generation failed"),
                    current_step="draft_generation",
                    pipeline_run_id=pipeline_uuid,
                )
                return result

            if workflow_result.status == "ok" and workflow_result.draft_id:
                run_outreach_draft_automation(
                    db,
                    uuid.UUID(workflow_result.draft_id),
                )

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
            logger.info(
                "task_step_completed",
                task_name="task_generate_draft",
                result=result,
            )
            return result
    except SoftTimeLimitExceeded:
        logger.error("task_soft_time_limit", task_name="task_generate_draft", task_id=task_id)
        with SessionLocal() as db:
            mark_task_failed(
                db,
                task_id=task_id,
                error="Soft time limit exceeded (5min)",
                current_step="draft_generation",
                pipeline_run_id=pipeline_uuid,
            )
        raise
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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
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
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()


@celery_app.task(bind=True)
def task_full_pipeline(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Dispatch the pipeline: enrich -> score -> analyze.

    Each step chains to the next via pipeline_run_id.
    Analyze decides the path based on lead quality.
    """
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

            # Dispatch only the first step; each step chains forward.
            task_enrich_lead.delay(
                lead_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
            )
            payload = {
                "status": "pipeline_started",
                "lead_id": lead_id,
                "pipeline_run_id": pipeline_run_id,
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

@celery_app.task(name="app.workers.tasks.task_batch_pipeline", bind=True, max_retries=0, soft_time_limit=7200, time_limit=7500)
def task_batch_pipeline(self, status_filter: str = "new", correlation_id: str | None = None):
    """Process ALL leads with the given status through the full pipeline, one by one.

    Canonical progress is tracked in TaskRun and mirrored to Redis for compatibility.
    """
    from app.services.enrichment_service import enrich_lead
    from app.services.outreach_service import generate_outreach_draft as _generate_draft
    from app.services.scoring_service import score_lead

    task_id = _request_task_id(self.request)
    queue = _queue_name(self.request, "default")

    from app.models.territory import Territory

    total_processed = 0
    total_errors = 0
    crawl_rounds = 0

    progress = build_batch_pipeline_progress(task_id=task_id)

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
        persist_operational_task_state(
            task_id,
            current_step="batch_dispatch",
            progress_json=progress,
            clear_error=True,
        )

        while True:
            if should_stop_operational_task(
                task_id=task_id,
                redis_key=BATCH_PIPELINE_REDIS_KEY,
            ):
                progress["status"] = "stopped"
                mirror_batch_pipeline_state(progress)
                persist_operational_task_state(
                    task_id,
                    current_step=progress.get("current_step"),
                    progress_json=progress,
                    status="stopped",
                    finished=True,
                )
                logger.info("batch_pipeline_stopped_by_user")
                return {"status": "stopped", "task_id": task_id}

            territory_info = None
            with SessionLocal() as db:
                # Load pending leads
                leads = db.query(Lead).filter(Lead.status == status_filter).order_by(Lead.created_at).all()
                lead_ids = [lead.id for lead in leads]

                if not leads:
                    # No leads — try crawling
                    territories = db.query(Territory).all()
                    territory_info = (str(territories[0].id), territories[0].name) if territories else None

            if not lead_ids:
                if not territory_info or crawl_rounds >= 3:
                    # No territories or max crawl rounds reached — done
                    break

                territory_id_str, territory_name = territory_info
                crawl_rounds += 1
                progress["current_step"] = "crawling"
                progress["current_lead"] = f"Crawling {territory_name} (ronda {crawl_rounds})"
                progress["crawl_rounds"] = crawl_rounds
                mirror_batch_pipeline_state(progress)
                persist_operational_task_state(
                    task_id,
                    current_step="crawling",
                    progress_json=progress,
                )
                logger.info("batch_auto_crawl", territory=territory_name, round=crawl_rounds)

                try:
                    task_crawl_territory(
                        territory_id=territory_id_str,
                        categories=None,
                        only_without_website=False,
                        max_results_per_category=20,
                        correlation_id=correlation_id,
                    )
                except Exception as crawl_exc:
                    logger.error("batch_auto_crawl_failed", territory=territory_name, round=crawl_rounds, error=str(crawl_exc))
                    total_errors += 1
                    progress["errors"] = total_errors
                    mirror_batch_pipeline_state(progress)
                    persist_operational_task_state(
                        task_id,
                        current_step="crawling",
                        progress_json=progress,
                    )
                    continue

                with SessionLocal() as db:
                    new_leads = db.query(Lead).filter(Lead.status == status_filter).order_by(Lead.created_at).all()
                    lead_ids = [lead.id for lead in new_leads]

                progress["leads_from_crawl"] = progress.get("leads_from_crawl", 0) + len(lead_ids)
                progress["crawl_rounds"] = crawl_rounds
                mirror_batch_pipeline_state(progress)
                persist_operational_task_state(
                    task_id,
                    current_step="crawling",
                    progress_json=progress,
                )
                logger.info("batch_post_crawl", new_leads=len(lead_ids), round=crawl_rounds)

                if not lead_ids:
                    break  # Crawl brought nothing new

            # Reset crawl counter — we have leads to process, so next crawl is fresh
            crawl_rounds = 0

            # Process this batch of leads
            batch_total = len(lead_ids)
            progress["total"] = total_processed + batch_total
            mirror_batch_pipeline_state(progress)
            persist_operational_task_state(
                task_id,
                current_step=progress.get("current_step"),
                progress_json=progress,
            )

            for idx, lead_id in enumerate(lead_ids):
                if should_stop_operational_task(
                    task_id=task_id,
                    redis_key=BATCH_PIPELINE_REDIS_KEY,
                    treat_missing_legacy_as_stop=True,
                ):
                    progress["status"] = "stopped"
                    mirror_batch_pipeline_state(progress)
                    persist_operational_task_state(
                        task_id,
                        current_step=progress.get("current_step"),
                        progress_json=progress,
                        status="stopped",
                        finished=True,
                    )
                    logger.info("batch_pipeline_stopped_by_user")
                    return {"status": "stopped", "task_id": task_id}

                progress["processed"] = total_processed + idx
                progress["current_step"] = "enrichment"
                mirror_batch_pipeline_state(progress)
                persist_operational_task_state(
                    task_id,
                    current_step="enrichment",
                    progress_json=progress,
                )

                try:
                    with SessionLocal() as db:
                        lead = db.get(Lead, lead_id)
                        if not lead:
                            continue
                        progress["current_lead"] = lead.business_name
                        mirror_batch_pipeline_state(progress)
                        persist_operational_task_state(
                            task_id,
                            current_step="enrichment",
                            progress_json=progress,
                        )

                        # Step 1: Enrich
                        enrich_lead(db, lead.id)

                        # Step 2: Score
                        progress["current_step"] = "scoring"
                        mirror_batch_pipeline_state(progress)
                        persist_operational_task_state(
                            task_id,
                            current_step="scoring",
                            progress_json=progress,
                        )
                        score_lead(db, lead.id)

                        # Step 3: LLM Analysis
                        progress["current_step"] = "analysis"
                        mirror_batch_pipeline_state(progress)
                        persist_operational_task_state(
                            task_id,
                            current_step="analysis",
                            progress_json=progress,
                        )

                        db.refresh(lead)
                        from app.llm.client import evaluate_lead_quality, summarize_business
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
                        raw_quality = evaluation.get("quality", "unknown").lower().strip()
                        if raw_quality not in ("high", "medium", "low"):
                            logger.warning("quality_normalized_to_unknown", lead=lead.business_name, raw_quality=raw_quality)
                        lead.llm_quality = raw_quality if raw_quality in ("high", "medium", "low") else "unknown"
                        db.commit()

                        # Step 4: HIGH lane — research + brief
                        if lead.llm_quality == "high":
                            progress["current_step"] = "research"
                            mirror_batch_pipeline_state(progress)
                            persist_operational_task_state(
                                task_id,
                                current_step="research",
                                progress_json=progress,
                            )
                            try:
                                from app.services.research_service import run_research
                                run_research(db, lead.id)
                            except Exception as res_exc:
                                logger.warning(
                                    "batch_research_failed",
                                    lead=lead.business_name,
                                    error=str(res_exc),
                                )

                            progress["current_step"] = "brief"
                            mirror_batch_pipeline_state(progress)
                            persist_operational_task_state(
                                task_id,
                                current_step="brief",
                                progress_json=progress,
                            )
                            try:
                                from app.services.brief_service import generate_brief
                                generate_brief(db, lead.id)
                            except Exception as brief_exc:
                                logger.warning(
                                    "batch_brief_failed",
                                    lead=lead.business_name,
                                    error=str(brief_exc),
                                )

                        # Step 5: Generate draft (only for high quality with email)
                        progress["current_step"] = "draft"
                        mirror_batch_pipeline_state(progress)
                        persist_operational_task_state(
                            task_id,
                            current_step="draft",
                            progress_json=progress,
                        )
                        if lead.llm_quality == "high" and lead.email:
                            _generate_draft(db, lead.id)
                        else:
                            reason = (
                                "no_email" if not lead.email
                                else ("quality=%s" % lead.llm_quality)
                            )
                            logger.info(
                                "batch_draft_skipped",
                                lead=lead.business_name,
                                reason=reason,
                            )

                        logger.info("batch_pipeline_lead_done", lead=lead.business_name, idx=total_processed + idx + 1)

                except Exception as exc:
                    total_errors += 1
                    progress["errors"] = total_errors
                    mirror_batch_pipeline_state(progress)
                    persist_operational_task_state(
                        task_id,
                        current_step=progress.get("current_step"),
                        progress_json=progress,
                    )
                    logger.error("batch_pipeline_lead_error", lead_id=str(lead_id), error=str(exc))

            total_processed += batch_total

        # Done
        progress["status"] = "done"
        progress["processed"] = total_processed
        progress["total"] = total_processed
        progress["current_lead"] = None
        progress["current_step"] = ""
        mirror_batch_pipeline_state(progress)
        persist_operational_task_state(
            task_id,
            current_step="completed",
            progress_json=progress,
            status="succeeded",
            clear_error=True,
            finished=True,
            result={
                "status": "done",
                "task_id": task_id,
                "total": total_processed,
                "errors": total_errors,
            },
            stop_requested=False,
        )
        logger.info("batch_pipeline_done", total=total_processed, errors=total_errors, crawl_rounds=crawl_rounds)
        return {"status": "done", "task_id": task_id, "total": total_processed, "errors": total_errors}

    except Exception as exc:
        mirror_batch_pipeline_state(
            {"status": "error", "task_id": task_id, "error": str(exc)}
        )
        persist_operational_task_state(
            task_id,
            current_step=progress.get("current_step"),
            progress_json=progress,
            status="failed",
            error=str(exc),
            finished=True,
        )
        logger.error("batch_pipeline_error", error=str(exc))
        raise
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

    def mirror_status(payload: dict) -> None:
        mirror_legacy_operational_state(RESCORE_ALL_REDIS_KEY, payload)

    def persist_state(
        *,
        total: int,
        rescored: int,
        current_lead_id: str | None = None,
        status: str | None = None,
        error: str | None = None,
        clear_error: bool = False,
        finished: bool = False,
        result: dict | None = None,
        stop_requested: bool | None = None,
    ) -> None:
        progress = build_rescore_all_progress(
            total=total,
            rescored=rescored,
            errors=errors,
            current_lead_id=current_lead_id,
        )
        with SessionLocal() as db:
            update_task_run(
                db,
                task_id,
                status=status,
                current_step=current_step,
                progress_json=progress,
                result=result,
                error=error,
                clear_error=clear_error,
                finished=finished,
                stop_requested=stop_requested,
        )

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
        persist_state(total=total, rescored=rescored, clear_error=True)
        mirror_status(
            {
                "status": "running",
                "task_id": task_id,
                "total": total,
                "rescored": rescored,
                "errors": 0,
                "current_step": current_step,
            }
        )

        for lead_id in lead_ids:
            current_step = "rescore_scoring"
            persist_state(total=total, rescored=rescored, current_lead_id=str(lead_id))

            with SessionLocal() as db:
                if is_task_stop_requested(db, task_id):
                    current_step = "rescore_stopped"
                    persist_state(
                        total=total,
                        rescored=rescored,
                        status="stopped",
                        finished=True,
                    )
                    mirror_status(
                        {
                            "status": "stopped",
                            "task_id": task_id,
                            "total": total,
                            "rescored": rescored,
                            "errors": errors,
                            "current_step": current_step,
                        }
                    )
                    logger.info("rescore_all_stopped_by_user")
                    return {"status": "stopped", "task_id": task_id}

            try:
                with SessionLocal() as db:
                    score_lead(db, lead_id)
                rescored += 1
            except Exception as exc:
                errors += 1
                logger.error("rescore_lead_error", lead_id=str(lead_id), error=str(exc))
            persist_state(
                total=total,
                rescored=rescored,
                current_lead_id=None,
            )

            processed_count = rescored + errors
            if processed_count % 20 == 0 or processed_count == total:
                mirror_status(
                    {
                        "status": "running",
                        "task_id": task_id,
                        "total": total,
                        "rescored": rescored,
                        "errors": errors,
                        "current_step": current_step,
                    }
                )

        current_step = "rescore_completed"
        result = {
            "status": "done",
            "task_id": task_id,
            "total": total,
            "rescored": rescored,
            "errors": errors,
        }
        persist_state(
            total=total,
            rescored=rescored,
            current_lead_id=None,
            status="succeeded",
            clear_error=True,
            finished=True,
            result=result,
            stop_requested=False,
        )
        mirror_status(
            {
                "status": "done",
                "task_id": task_id,
                "total": total,
                "rescored": rescored,
                "errors": errors,
                "current_step": current_step,
            }
        )
        logger.info("rescore_all_done", total=total, rescored=rescored, errors=errors)
        return result
    except Exception as exc:
        persist_state(
            total=total,
            rescored=rescored,
            current_lead_id=None,
            status="failed",
            error=str(exc),
            finished=True,
        )
        mirror_status(
            {
                "status": "error",
                "task_id": task_id,
                "total": total,
                "rescored": rescored,
                "errors": errors,
                "current_step": current_step,
                "error": str(exc),
            }
        )
        logger.error("rescore_all_error", error=str(exc))
        raise
    finally:
        clear_tracking_context()


# ── Google Maps crawl task ────────────────────────────────────────────

@celery_app.task(name="app.workers.tasks.task_crawl_territory", bind=True, max_retries=0)
def task_crawl_territory(
    self,
    territory_id: str,
    categories: list[str] | None = None,
    only_without_website: bool = False,
    max_results_per_category: int = 20,
    target_leads: int = 50,
    correlation_id: str | None = None,
):
    """Crawl Google Maps for all cities in a territory."""
    from app.crawlers.google_maps_crawler import GoogleMapsCrawler
    from app.models.lead_source import LeadSource, SourceType
    from app.models.territory import Territory
    from app.schemas.lead import LeadCreate
    from app.services.lead_service import _compute_dedup_hash, create_lead

    redis_key = territory_crawl_redis_key(territory_id)
    task_id = _request_task_id(self.request)
    queue = _queue_name(self.request, "default")

    progress = build_territory_crawl_progress(task_id=task_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                task_id=task_id,
                correlation_id=correlation_id,
                current_step="crawl_init",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_crawl_territory",
                queue=queue,
                correlation_id=correlation_id,
                scope_key=territory_id,
                current_step="crawl_init",
            )

        # Load territory metadata and ensure source exists in a short-lived session
        with SessionLocal() as db:
            territory = db.get(Territory, uuid.UUID(territory_id))
            if not territory:
                mirror_territory_crawl_state(
                    territory_id,
                    {"status": "error", "error": "Territorio no encontrado"},
                )
                persist_operational_task_state(
                    task_id,
                    current_step="crawl_init",
                    progress_json=progress,
                    status="failed",
                    error="Territorio no encontrado",
                    finished=True,
                )
                return

            cities = list(territory.cities or [])
            territory_name = territory.name
            if not cities:
                mirror_territory_crawl_state(
                    territory_id,
                    {"status": "error", "error": "El territorio no tiene ciudades"},
                )
                persist_operational_task_state(
                    task_id,
                    current_step="crawl_init",
                    progress_json=progress,
                    status="failed",
                    error="El territorio no tiene ciudades",
                    finished=True,
                )
                return

            source = db.query(LeadSource).filter(LeadSource.name == "google_maps").first()
            if not source:
                source = LeadSource(name="google_maps", source_type=SourceType.CRAWLER, description="Google Maps Places API")
                db.add(source)
                db.commit()
                db.refresh(source)
            source_id = source.id

        progress["territory"] = territory_name
        progress["total_cities"] = len(cities)
        persist_operational_task_state(
            task_id,
            current_step="crawl_init",
            progress_json=progress,
            clear_error=True,
        )

        crawler = GoogleMapsCrawler()
        total_found = 0
        total_created = 0
        total_dup = 0
        mirror_territory_crawl_state(territory_id, progress)

        for idx, city in enumerate(cities):
            if should_stop_operational_task(
                task_id=task_id,
                redis_key=redis_key,
                treat_missing_legacy_as_stop=True,
            ):
                progress["status"] = "stopped"
                mirror_territory_crawl_state(territory_id, progress)
                persist_operational_task_state(
                    task_id,
                    current_step=progress.get("current_step"),
                    progress_json=progress,
                    status="stopped",
                    finished=True,
                )
                logger.info("territory_crawl_stopped_by_user", territory=territory_name)
                return

            progress["current_city_idx"] = idx + 1
            progress["current_city"] = city
            progress["current_step"] = "crawling"
            mirror_territory_crawl_state(territory_id, progress)
            persist_operational_task_state(
                task_id,
                current_step="crawling",
                progress_json=progress,
            )

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

            with SessionLocal() as db:
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
                            source_id=source_id,
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
            mirror_territory_crawl_state(territory_id, progress)
            persist_operational_task_state(
                task_id,
                current_step="crawling",
                progress_json=progress,
            )

        progress["status"] = "done"
        mirror_territory_crawl_state(territory_id, progress)
        persist_operational_task_state(
            task_id,
            current_step="completed",
            progress_json=progress,
            status="succeeded",
            clear_error=True,
            finished=True,
            result={
                "status": "done",
                "task_id": task_id,
                "territory": territory_name,
                "found": total_found,
                "created": total_created,
                "skipped": total_dup,
            },
            stop_requested=False,
        )

        logger.info(
            "territory_crawl_done",
            territory=territory_name,
            cities=len(cities),
            found=total_found,
            created=total_created,
            skipped=total_dup,
        )
    except Exception as exc:
        mirror_territory_crawl_state(
            territory_id,
            {"status": "error", "error": str(exc)},
        )
        persist_operational_task_state(
            task_id,
            current_step=progress.get("current_step"),
            progress_json=progress,
            status="failed",
            error=str(exc),
            finished=True,
        )
        logger.error("territory_crawl_error", territory_id=territory_id, error=str(exc))
        raise
    finally:
        clear_tracking_context()


@celery_app.task(
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=120,
    time_limit=180,
)
def task_research_lead(
    self,
    lead_id: str,
    pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Async task: run web research on a lead's digital presence."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "research")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                correlation_id=correlation_id,
                current_step="research",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_research_lead",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                correlation_id=correlation_id,
                current_step="research",
            )

            from app.services.research_service import run_research

            report = run_research(db, uuid.UUID(lead_id))
            if not report:
                error = "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error,
                    current_step="research",
                    pipeline_run_id=pipeline_uuid,
                )
                return {"status": "not_found", "lead_id": lead_id}

            # Generate dossier from research data
            if report.status.value == "completed":
                try:
                    from app.llm.client import generate_dossier
                    lead = db.get(Lead, uuid.UUID(lead_id))
                    if lead and report:
                        dossier = generate_dossier(
                            business_name=lead.business_name,
                            industry=lead.industry,
                            city=lead.city,
                            website_url=lead.website_url,
                            instagram_url=lead.instagram_url,
                            score=lead.score,
                            signals=", ".join(
                                s.get("type", "") for s in (report.detected_signals_json or [])
                            ),
                            html_metadata=str(report.html_metadata_json or {}),
                            website_confidence=(
                                report.website_confidence.value
                                if report.website_confidence else "unknown"
                            ),
                            instagram_confidence=(
                                report.instagram_confidence.value
                                if report.instagram_confidence else "unknown"
                            ),
                            whatsapp_detected=str(report.whatsapp_detected or False),
                        )
                        if dossier:
                            report.business_description = dossier.get("business_description")
                            db.commit()
                            logger.info("dossier_generated_in_pipeline", lead_id=lead_id)
                except Exception as dossier_exc:
                    logger.warning(
                        "dossier_generation_failed_in_pipeline",
                        lead_id=lead_id,
                        error=str(dossier_exc),
                    )

                # Emit notification
                try:
                    from app.services.notification_emitter import on_research_completed
                    lead = db.get(Lead, uuid.UUID(lead_id))
                    on_research_completed(
                        db,
                        lead_id=uuid.UUID(lead_id),
                        business_name=lead.business_name if lead else None,
                        signals_count=len(report.detected_signals_json or []),
                    )
                except Exception:
                    pass

                # Chain: generate brief for HIGH leads
                if pipeline_run_id:
                    try:
                        from app.workers.brief_tasks import task_generate_brief
                        task_generate_brief.delay(lead_id, pipeline_run_id)
                        logger.info("brief_chained_from_research", lead_id=lead_id)
                    except Exception as chain_exc:
                        logger.warning(
                            "brief_chain_failed",
                            lead_id=lead_id,
                            error=str(chain_exc),
                        )

            result = {
                "status": report.status.value,
                "lead_id": lead_id,
                "duration_ms": report.research_duration_ms,
            }
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="research",
                pipeline_run_id=pipeline_uuid,
            )
            logger.info(
                "task_step_completed",
                task_name="task_research_lead",
                result=result,
            )
            return result
    except SoftTimeLimitExceeded:
        logger.error(
            "task_soft_time_limit",
            task_name="task_research_lead",
            task_id=task_id,
        )
        with SessionLocal() as db:
            mark_task_failed(
                db,
                task_id=task_id,
                error="Soft time limit exceeded (2min)",
                current_step="research",
                pipeline_run_id=pipeline_uuid,
            )
        raise
    except Exception as exc:
        _track_failure(
            task=self,
            task_name="task_research_lead",
            task_id=task_id,
            lead_id=lead_id,
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="research",
            queue=queue,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        clear_tracking_context()
