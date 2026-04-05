"""Celery tasks for lead research."""

import uuid

from celery.exceptions import SoftTimeLimitExceeded

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.lead import Lead
from app.services.pipeline.task_tracking_service import (
    mark_task_failed,
    tracked_task_step,
)
from app.workers._helpers import _pipeline_uuid, _queue_name, _track_failure
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.tasks.task_research_lead",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=360,
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
        with SessionLocal() as db, tracked_task_step(
            db,
            task_id=task_id,
            task_name="task_research_lead",
            queue=queue,
            lead_id=uuid.UUID(lead_id),
            pipeline_run_id=pipeline_uuid,
            correlation_id=correlation_id,
            current_step="research",
        ) as tracker:

            from app.services.research.research_service import run_research

            # Try Scout agent first (deep investigation with tools)
            scout_result = None
            try:
                from app.agent.research_agent import run_scout_investigation
                from app.services.pipeline.context_service import get_step_context

                # Get analysis context from upstream pipeline
                analysis_ctx = ""
                if pipeline_uuid:
                    ctx = get_step_context(db, pipeline_uuid)
                    analysis = ctx.get("analysis", {})
                    analysis_ctx = f"Quality: {analysis.get('quality', '?')}. {analysis.get('reasoning', '')}"

                lead = db.get(Lead, uuid.UUID(lead_id))
                if lead:
                    scout_result = run_scout_investigation(
                        business_name=lead.business_name,
                        industry=lead.industry,
                        city=lead.city,
                        website_url=lead.website_url,
                        instagram_url=lead.instagram_url,
                        score=lead.score,
                        signals=", ".join(s.signal_type for s in lead.signals) if lead.signals else "",
                        analysis_context=analysis_ctx,
                    )
                    logger.info(
                        "scout_investigation_done",
                        lead_id=lead_id,
                        loops=scout_result.loops_used,
                        duration_ms=scout_result.duration_ms,
                        has_findings=bool(scout_result.findings),
                        error=scout_result.error,
                    )

                    # Store investigation thread for dashboard
                    from app.models.investigation_thread import InvestigationThread
                    from app.llm.resolver import resolve_model_for_role
                    from app.llm.roles import LLMRole

                    thread = InvestigationThread(
                        lead_id=uuid.UUID(lead_id),
                        pipeline_run_id=pipeline_uuid,
                        agent_model=resolve_model_for_role(LLMRole.EXECUTOR) or "unknown",
                        tool_calls_json=scout_result.tool_calls,
                        pages_visited_json=scout_result.pages_visited,
                        findings_json=scout_result.findings,
                        loops_used=scout_result.loops_used,
                        duration_ms=scout_result.duration_ms,
                        error=scout_result.error,
                    )
                    db.add(thread)
                    db.commit()

                    # Write structured Scout context for downstream steps
                    if pipeline_uuid and scout_result.findings:
                        from app.services.pipeline.context_service import append_step_context
                        append_step_context(db, pipeline_uuid, "scout", {
                            "pages_visited": len(scout_result.pages_visited or []),
                            "opportunity": scout_result.findings.get("opportunity", ""),
                            "whatsapp_detected": scout_result.findings.get("whatsapp_detected", False),
                            "findings_summary": scout_result.findings.get("summary", ""),
                            "loops_used": scout_result.loops_used,
                        })
            except Exception as scout_exc:
                logger.warning(
                    "scout_fallback_to_http",
                    lead_id=lead_id,
                    error=str(scout_exc),
                )
                scout_result = None

            # Run HTTP research (always — provides base signals and report record)
            report = run_research(db, uuid.UUID(lead_id))
            if not report:
                error = "Lead not found"
                tracker.fail(error)
                return {"status": "not_found", "lead_id": lead_id}

            # Enrich report with Scout findings if available
            if scout_result and scout_result.findings and not scout_result.error:
                findings = scout_result.findings
                if findings.get("opportunity"):
                    report.business_description = (
                        (report.business_description or "") + " | Scout: " + findings["opportunity"]
                    )
                if findings.get("whatsapp_detected"):
                    report.whatsapp_detected = True
                db.commit()

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
                                s.get("type", "")
                                for s in (report.detected_signals_json or [])
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
                            whatsapp_detected=str(
                                report.whatsapp_detected or False
                            ),
                        )
                        if dossier:
                            report.business_description = dossier.get(
                                "business_description"
                            )
                            db.commit()
                            logger.info(
                                "dossier_generated_in_pipeline", lead_id=lead_id
                            )
                except Exception as dossier_exc:
                    logger.warning(
                        "dossier_generation_failed_in_pipeline",
                        lead_id=lead_id,
                        error=str(dossier_exc),
                    )

                # Emit notification
                try:
                    from app.services.notifications.notification_emitter import (
                        on_research_completed,
                    )
                    lead = db.get(Lead, uuid.UUID(lead_id))
                    on_research_completed(
                        db,
                        lead_id=uuid.UUID(lead_id),
                        business_name=lead.business_name if lead else None,
                        signals_count=len(report.detected_signals_json or []),
                    )
                except Exception as exc:
                    logger.debug("research_notification_failed", error=str(exc))

                # Write research context for downstream steps
                if pipeline_uuid:
                    from app.services.pipeline.context_service import append_step_context
                    append_step_context(db, pipeline_uuid, "research", {
                        "status": report.status.value,
                        "website_exists": report.website_exists,
                        "whatsapp_detected": report.whatsapp_detected,
                        "signals": report.detected_signals_json,
                        "business_description": report.business_description,
                    })

                # Chain: generate brief for HIGH leads
                if pipeline_run_id:
                    try:
                        from app.workers.brief_tasks import task_generate_brief
                        task_generate_brief.delay(lead_id, pipeline_run_id, correlation_id=correlation_id)
                        logger.info(
                            "brief_chained_from_research", lead_id=lead_id
                        )
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
            tracker.succeed(result)
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
