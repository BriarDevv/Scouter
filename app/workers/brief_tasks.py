"""Celery tasks for commercial brief generation and review."""

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.task_tracking_service import (
    bind_tracking_context,
    clear_tracking_context,
    mark_task_failed,
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


@celery_app.task(
    name="app.workers.brief_tasks.task_generate_brief",
    bind=True,
    max_retries=1,
    soft_time_limit=120,
    time_limit=150,
)
def task_generate_brief(
    self, lead_id: str, pipeline_run_id: str | None = None
):
    """Generate a commercial brief for a lead asynchronously."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "llm")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                current_step="brief_generation",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_generate_brief",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                current_step="brief_generation",
            )

            from app.services.brief_service import generate_brief

            brief = generate_brief(db, uuid.UUID(lead_id))
            if brief and brief.status.value == "generated":
                result = {
                    "status": "ok",
                    "lead_id": lead_id,
                    "opportunity_score": brief.opportunity_score,
                }
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="brief_generation",
                    pipeline_run_id=pipeline_uuid,
                )
                logger.info(
                    "task_generate_brief_done",
                    lead_id=lead_id,
                    opportunity_score=brief.opportunity_score,
                )
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
            else:
                error_msg = brief.error if brief else "Lead not found"
                mark_task_failed(
                    db,
                    task_id=task_id,
                    error=error_msg or "unknown",
                    current_step="brief_generation",
                    pipeline_run_id=pipeline_uuid,
                )
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
    finally:
        clear_tracking_context()


@celery_app.task(
    name="app.workers.brief_tasks.task_review_brief",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def task_review_brief(
    self, lead_id: str, pipeline_run_id: str | None = None
):
    """Review a commercial brief with the REVIEWER model."""
    task_id = str(self.request.id)
    queue = _queue_name(self.request, "reviewer")
    pipeline_uuid = _pipeline_uuid(pipeline_run_id)

    try:
        with SessionLocal() as db:
            bind_tracking_context(
                lead_id=lead_id,
                task_id=task_id,
                pipeline_run_id=pipeline_run_id,
                current_step="brief_review",
            )
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_review_brief",
                queue=queue,
                lead_id=uuid.UUID(lead_id),
                pipeline_run_id=pipeline_uuid,
                current_step="brief_review",
            )

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
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="brief_review",
                    pipeline_run_id=pipeline_uuid,
                )
                return result

            # Build review prompt
            review_data = (
                f"Opportunity Score: {brief.opportunity_score}\n"
                f"Budget Tier: {brief.budget_tier.value if brief.budget_tier else 'N/A'}\n"
                f"Scope: {brief.estimated_scope.value if brief.estimated_scope else 'N/A'}\n"
                f"Contact: {brief.recommended_contact_method.value if brief.recommended_contact_method else 'N/A'}\n"
                f"Should Call: {brief.should_call.value if brief.should_call else 'N/A'}\n"
                f"Call Reason: {brief.call_reason or 'N/A'}\n"
                f"Why Matters: {brief.why_this_lead_matters or 'N/A'}\n"
                f"Angle: {brief.recommended_angle or 'N/A'}\n"
            )
            system_prompt = (
                "Sos un reviewer comercial senior. Revisá el brief y respondé "
                'con JSON: {"approved": true/false, "feedback": "...", '
                '"suggested_changes": "..."}'
            )

            from app.llm.client import _call_ollama_chat, _extract_json
            from app.llm.roles import LLMRole

            raw = _call_ollama_chat(system_prompt, review_data, role=LLMRole.REVIEWER)
            review_result = _extract_json(raw)

            from datetime import datetime, timezone
            brief.reviewer_model = "reviewer"
            brief.reviewed_at = datetime.now(timezone.utc)
            if review_result and review_result.get("approved"):
                brief.status = BriefStatus.REVIEWED
            db.commit()

            result = {
                "status": "ok",
                "lead_id": lead_id,
                "approved": review_result.get("approved") if review_result else None,
            }
            mark_task_succeeded(
                db,
                task_id=task_id,
                result=result,
                current_step="brief_review",
                pipeline_run_id=pipeline_uuid,
            )

            # Chain to draft generation (pipeline finalized there)
            if pipeline_uuid:
                from app.workers.tasks import task_generate_draft
                task_generate_draft.delay(lead_id, pipeline_run_id)
                logger.info(
                    "draft_chained_from_brief_review",
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
    finally:
        clear_tracking_context()
