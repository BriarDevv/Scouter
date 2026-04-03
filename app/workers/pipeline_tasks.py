"""Celery tasks for the lead processing pipeline."""

import uuid

from celery.exceptions import SoftTimeLimitExceeded

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.llm.roles import LLMRole
from app.models.lead import Lead
from app.services.leads.enrichment_service import enrich_lead
from app.services.leads.scoring_service import score_lead
from app.services.pipeline.task_tracking_service import (
    bind_tracking_context,
    clear_tracking_context,
    mark_task_failed,
    mark_task_retrying,
    mark_task_running,
    tracked_task_step,
)
from app.workers.celery_app import celery_app
from app.workflows.lead_pipeline import (
    run_draft_generation_step,
    run_lead_analysis_step,
)
from app.workflows.outreach_draft_generation import should_generate_outreach_email_draft

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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_enrich_lead",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="enrichment",
        ) as tracker:

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            # Idempotency guard: skip if already enriched (unless force)
            if lead.enriched_at is not None:
                result = {"status": "skipped", "lead_id": lead_id, "reason": "already_enriched"}
                tracker.succeed(result)
                logger.info(
                    "task_skipped_idempotent",
                    task_name="task_enrich_lead",
                    lead_id=lead_id,
                )
                return result

            lead = enrich_lead(db, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            result = {"status": "ok", "lead_id": lead_id, "signals": len(lead.signals)}
            tracker.succeed(result)
            logger.info("task_step_completed", task_name="task_enrich_lead", result=result)

            # Write enrichment context for downstream steps
            if pipeline_uuid:
                from app.services.pipeline.context_service import append_step_context
                append_step_context(db, pipeline_uuid, "enrichment", {
                    "signals": [s.signal_type for s in lead.signals],
                    "email_found": lead.email is not None,
                    "website_exists": lead.website_url is not None,
                    "instagram_exists": lead.instagram_url is not None,
                })

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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_score_lead",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="scoring",
        ) as tracker:

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            # Idempotency guard: skip if already scored
            if lead.scored_at is not None:
                result = {
                    "status": "skipped",
                    "lead_id": lead_id,
                    "reason": "already_scored",
                    "score": lead.score,
                }
                tracker.succeed(result)
                logger.info(
                    "task_skipped_idempotent",
                    task_name="task_score_lead",
                    lead_id=lead_id,
                )
                return result

            lead = score_lead(db, uuid.UUID(lead_id))
            if not lead:
                error = "Score failed"
                tracker.fail(error)
                return {"status": "failed", "lead_id": lead_id}

            result = {"status": "ok", "lead_id": lead_id, "score": lead.score}
            tracker.succeed(result)
            logger.info("task_step_completed", task_name="task_score_lead", result=result)

            # Write scoring context for downstream steps
            if pipeline_uuid:
                from app.services.pipeline.context_service import append_step_context
                append_step_context(db, pipeline_uuid, "scoring", {
                    "score": lead.score,
                    "signal_count": len(lead.signals),
                })

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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_analyze_lead",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="analysis",
        ) as tracker:

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            # Idempotency guard: skip if already analyzed
            if lead.llm_summary is not None:
                result = {
                    "status": "skipped",
                    "lead_id": lead_id,
                    "reason": "already_analyzed",
                    "quality": lead.llm_quality,
                }
                tracker.succeed(result)
                logger.info(
                    "task_skipped_idempotent",
                    task_name="task_analyze_lead",
                    lead_id=lead_id,
                )
                return result

            analysis = run_lead_analysis_step(
                db,
                lead,
                source_tag="task_analyze_lead",
                role=LLMRole.EXECUTOR,
            )

            db.commit()
            result = {
                "status": "ok",
                "lead_id": lead_id,
                "quality": analysis.quality,
            }
            tracker.succeed(result)
            logger.info(
                "task_step_completed", task_name="task_analyze_lead", result=result
            )

            # Write analysis context for downstream steps
            if pipeline_uuid:
                from app.services.pipeline.context_service import append_step_context
                append_step_context(db, pipeline_uuid, "analysis", {
                    "quality": analysis.quality,
                    "reasoning": analysis.reasoning,
                    "suggested_angle": analysis.suggested_angle,
                    "summary": getattr(lead, "llm_summary", None),
                })

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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_generate_draft",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="draft_generation",
        ) as tracker:

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            workflow_result = run_draft_generation_step(db, uuid.UUID(lead_id))
            result = workflow_result.to_payload()

            if workflow_result.status == "not_found":
                tracker.fail("Lead not found")
                return result

            if workflow_result.status == "failed":
                tracker.fail(str(workflow_result.reason or "Draft generation failed"))
                return result

            tracker.succeed(
                result,
                pipeline_status="succeeded" if pipeline_uuid else None,
            )
            if pipeline_uuid:
                with SessionLocal() as pipeline_db:
                    from app.services.pipeline.task_tracking_service import update_pipeline_run

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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_full_pipeline",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="pipeline_dispatch",
        ) as tracker:

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
            tracker.succeed(payload, pipeline_status="running" if pipeline_uuid else None)
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
