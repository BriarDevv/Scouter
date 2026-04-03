"""Celery tasks for the lead processing pipeline."""

import uuid

from celery.exceptions import SoftTimeLimitExceeded

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.llm.client import evaluate_lead_quality_structured, summarize_business
from app.llm.roles import LLMRole
from app.models.lead import Lead
from app.services.enrichment_service import enrich_lead
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


@celery_app.task(
    name="app.workers.tasks.task_enrich_lead",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
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
                logger.info(
                    "task_skipped_idempotent",
                    task_name="task_enrich_lead",
                    lead_id=lead_id,
                )
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


@celery_app.task(
    name="app.workers.tasks.task_score_lead",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
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
                result = {
                    "status": "skipped",
                    "lead_id": lead_id,
                    "reason": "already_scored",
                    "score": lead.score,
                }
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="scoring",
                    pipeline_run_id=pipeline_uuid,
                )
                logger.info(
                    "task_skipped_idempotent",
                    task_name="task_score_lead",
                    lead_id=lead_id,
                )
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


@celery_app.task(
    name="app.workers.tasks.task_analyze_lead",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
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
                logger.info(
                    "task_skipped_idempotent",
                    task_name="task_analyze_lead",
                    lead_id=lead_id,
                )
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

            evaluation = evaluate_lead_quality_structured(
                business_name=lead.business_name,
                industry=lead.industry,
                city=lead.city,
                website_url=lead.website_url,
                instagram_url=lead.instagram_url,
                signals=list(lead.signals),
                score=lead.score,
                role=LLMRole.EXECUTOR,
                target_type="lead",
                target_id=lead_id,
                tags={"task_name": "task_analyze_lead"},
            )
            evaluation_payload = evaluation.parsed
            lead.llm_quality_assessment = (
                evaluation_payload.reasoning
                if evaluation_payload
                else "LLM analysis unavailable"
            )
            lead.llm_suggested_angle = (
                evaluation_payload.suggested_angle
                if evaluation_payload
                else "General web development services"
            )
            raw_quality = (
                evaluation_payload.quality.lower().strip()
                if evaluation_payload
                else "unknown"
            )
            if raw_quality not in ("high", "medium", "low"):
                logger.warning(
                    "quality_normalized_to_unknown",
                    lead=lead.business_name,
                    raw_quality=raw_quality,
                )
            lead.llm_quality = (
                raw_quality if raw_quality in ("high", "medium", "low") else "unknown"
            )

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
            logger.info(
                "task_step_completed", task_name="task_analyze_lead", result=result
            )

            # Chain next step based on quality
            if lead.llm_quality == "high":
                try:
                    from app.workers.research_tasks import task_research_lead

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
        logger.error(
            "task_soft_time_limit", task_name="task_analyze_lead", task_id=task_id
        )
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


@celery_app.task(
    name="app.workers.tasks.task_generate_draft",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
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
        logger.error(
            "task_soft_time_limit",
            task_name="task_generate_draft",
            task_id=task_id,
        )
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


@celery_app.task(
    name="app.workers.tasks.task_full_pipeline",
    bind=True,
)
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
