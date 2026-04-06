"""Celery tasks for commercial brief generation and review."""

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.pipeline.task_tracking_service import (
    mark_task_failed,
    tracked_task_step,
)
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def _queue_name(request, fallback: str) -> str:
    delivery_info = getattr(request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or delivery_info.get("queue") or fallback


def _pipeline_uuid(pipeline_run_id: str | None) -> uuid.UUID | None:
    return uuid.UUID(pipeline_run_id) if pipeline_run_id else None


@celery_app.task(
    name="app.workers.brief_tasks.task_generate_brief",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def task_generate_brief(
    self, lead_id: str, pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
):
    """Generate a commercial brief for a lead asynchronously."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "llm")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_generate_brief",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="brief_generation",
        ) as tracker:

            from app.services.research.brief_service import generate_brief

            brief = generate_brief(db, uuid.UUID(lead_id))
            if brief and brief.status.value == "generated":
                result = {
                    "status": "ok",
                    "lead_id": lead_id,
                    "opportunity_score": brief.opportunity_score,
                }
                tracker.succeed(result)
                logger.info(
                    "task_generate_brief_done",
                    lead_id=lead_id,
                    opportunity_score=brief.opportunity_score,
                )
                # Write brief context for downstream steps
                if pipeline_uuid:
                    from app.services.pipeline.context_service import append_step_context
                    append_step_context(db, pipeline_uuid, "brief", {
                        "opportunity_score": brief.opportunity_score,
                        "budget_tier": brief.budget_tier.value if brief.budget_tier else None,
                        "estimated_scope": brief.estimated_scope.value if brief.estimated_scope else None,
                        "recommended_contact_method": brief.recommended_contact_method.value if brief.recommended_contact_method else None,
                        "recommended_angle": brief.recommended_angle,
                        "why_this_lead_matters": brief.why_this_lead_matters,
                    })

                # Chain: review brief with REVIEWER
                try:
                    task_review_brief.delay(lead_id, pipeline_run_id)
                    logger.info("brief_review_chained", lead_id=lead_id)
                except Exception as chain_exc:
                    logger.warning(
                        "brief_review_chain_failed",
                        lead_id=lead_id,
                        error=str(chain_exc),
                    )
                return result

            error_msg = brief.error if brief else "Lead not found"
            tracker.fail(error_msg or "unknown")
            return {"status": "failed", "lead_id": lead_id, "error": error_msg}
    except Exception as exc:
        with SessionLocal() as db:
            mark_task_failed(
                db,
                task_id=task_id,
                error=str(exc)[:500],
                current_step="brief_generation",
                pipeline_run_id=pipeline_uuid,
            )
        logger.error("task_generate_brief_error", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(
    name="app.workers.brief_tasks.task_review_brief",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def task_review_brief(
    self, lead_id: str, pipeline_run_id: str | None = None,
    correlation_id: str | None = None,
):
    """Review a commercial brief with the REVIEWER model."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_review_brief",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="brief_review",
        ) as tracker:

            from app.models.commercial_brief import BriefStatus, CommercialBrief

            brief = db.query(CommercialBrief).filter_by(
                lead_id=uuid.UUID(lead_id)
            ).first()
            if not brief or brief.status != BriefStatus.GENERATED:
                result = {
                    "status": "skipped",
                    "lead_id": lead_id,
                    "reason": "no_generated_brief",
                }
                tracker.succeed(result)
                return result

            from app.llm.client import review_commercial_brief_structured
            from app.llm.roles import LLMRole

            review_result = review_commercial_brief_structured(
                opportunity_score=brief.opportunity_score,
                budget_tier=brief.budget_tier.value if brief.budget_tier else None,
                estimated_scope=brief.estimated_scope.value if brief.estimated_scope else None,
                recommended_contact_method=(
                    brief.recommended_contact_method.value
                    if brief.recommended_contact_method
                    else None
                ),
                should_call=brief.should_call.value if brief.should_call else None,
                call_reason=brief.call_reason,
                why_this_lead_matters=brief.why_this_lead_matters,
                main_business_signals=brief.main_business_signals or [],
                main_digital_gaps=brief.main_digital_gaps or [],
                recommended_angle=brief.recommended_angle,
                demo_recommended=brief.demo_recommended,
                role=LLMRole.REVIEWER,
                target_type="commercial_brief",
                target_id=str(brief.id),
                tags={"lead_id": lead_id},
            )
            review_payload = review_result.parsed

            from datetime import UTC, datetime

            brief.reviewer_model = review_result.model
            brief.reviewed_at = datetime.now(UTC)
            if review_payload and review_payload.approved:
                brief.status = BriefStatus.REVIEWED
            db.commit()

            # Write review context for downstream steps
            if pipeline_uuid:
                from app.services.pipeline.context_service import append_step_context
                append_step_context(db, pipeline_uuid, "brief_review", {
                    "approved": review_payload.approved if review_payload else None,
                    "verdict_reasoning": review_payload.feedback if review_payload else None,
                })

            result = {
                "status": "ok",
                "lead_id": lead_id,
                "approved": review_payload.approved if review_payload else None,
            }
            tracker.succeed(result)

            # Chain to draft generation only if brief was approved
            is_approved = review_payload.approved if review_payload else False
            if pipeline_uuid and is_approved:
                from app.workers.tasks import task_generate_draft

                task_generate_draft.delay(lead_id, pipeline_run_id)
                logger.info(
                    "draft_chained_from_brief_review",
                    lead_id=lead_id,
                )
            elif pipeline_uuid and not is_approved:
                logger.info(
                    "draft_skipped_brief_rejected",
                    lead_id=lead_id,
                )

            logger.info("task_review_brief_done", lead_id=lead_id, result=result)
            return result

    except Exception as exc:
        with SessionLocal() as db:
            mark_task_failed(
                db,
                task_id=task_id,
                error=str(exc)[:500],
                current_step="brief_review",
                pipeline_run_id=pipeline_uuid,
            )
        logger.error("task_review_brief_error", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
