"""Workflow helpers for the batch pipeline orchestration."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.lead import Lead
from app.models.territory import Territory
from app.services.leads.enrichment_service import enrich_lead
from app.services.leads.scoring_service import score_lead
from app.services.pipeline.operational_task_service import (
    BATCH_PIPELINE_REDIS_KEY,
    build_batch_pipeline_progress,
    mirror_batch_pipeline_state,
    persist_operational_task_state,
    should_stop_operational_task,
)
from app.workflows.lead_pipeline import (
    run_draft_generation_step,
    run_high_value_lane_inline,
    run_lead_analysis_step,
)
from app.workflows.territory_crawl import run_territory_crawl_workflow

logger = get_logger(__name__)


def run_batch_pipeline_workflow(
    *,
    task_id: str,
    status_filter: str = "new",
    correlation_id: str | None = None,
    crawl_territory_workflow: Callable[..., object] = run_territory_crawl_workflow,
) -> dict[str, object]:
    """Orchestrate the batch pipeline while delegating state projection to helpers."""
    total_processed = 0
    total_errors = 0
    crawl_rounds = 0
    progress = build_batch_pipeline_progress(task_id=task_id)

    def sync_progress(
        *,
        current_step: str | None = None,
        status: str | None = None,
        error: str | None = None,
        clear_error: bool = False,
        finished: bool = False,
        result: dict | None = None,
        stop_requested: bool | None = None,
        mirror: bool = True,
    ) -> None:
        if current_step is not None:
            progress["current_step"] = current_step
        if mirror:
            mirror_batch_pipeline_state(progress)
        persist_operational_task_state(
            task_id,
            current_step=progress.get("current_step"),
            progress_json=progress,
            status=status,
            error=error,
            clear_error=clear_error,
            finished=finished,
            result=result,
            stop_requested=stop_requested,
        )

    def stop_pipeline() -> dict[str, object]:
        progress["status"] = "stopped"
        sync_progress(status="stopped", finished=True)
        logger.info("batch_pipeline_stopped_by_user")
        return {"status": "stopped", "task_id": task_id}

    try:
        sync_progress(current_step="batch_dispatch", clear_error=True, mirror=False)

        while True:
            if should_stop_operational_task(
                task_id=task_id,
                redis_key=BATCH_PIPELINE_REDIS_KEY,
            ):
                return stop_pipeline()

            territory_info: tuple[str, str] | None = None
            with SessionLocal() as db:
                leads = (
                    db.query(Lead)
                    .filter(Lead.status == status_filter)
                    .order_by(Lead.created_at)
                    .all()
                )
                lead_ids = [lead.id for lead in leads]

                if not leads:
                    territories = db.query(Territory).all()
                    territory_info = (
                        (str(territories[0].id), territories[0].name)
                        if territories
                        else None
                    )

            if not lead_ids:
                if not territory_info or crawl_rounds >= 3:
                    break

                territory_id_str, territory_name = territory_info
                crawl_rounds += 1
                progress["current_step"] = "crawling"
                progress["current_lead"] = (
                    f"Crawling {territory_name} (ronda {crawl_rounds})"
                )
                progress["crawl_rounds"] = crawl_rounds
                sync_progress(current_step="crawling")
                logger.info(
                    "batch_auto_crawl",
                    territory=territory_name,
                    round=crawl_rounds,
                )

                try:
                    crawl_territory_workflow(
                        task_id=str(uuid.uuid4()),
                        territory_id=territory_id_str,
                        categories=None,
                        only_without_website=False,
                        max_results_per_category=20,
                        correlation_id=correlation_id,
                    )
                except Exception as crawl_exc:
                    logger.error(
                        "batch_auto_crawl_failed",
                        territory=territory_name,
                        round=crawl_rounds,
                        error=str(crawl_exc),
                    )
                    total_errors += 1
                    progress["errors"] = total_errors
                    sync_progress(current_step="crawling")
                    continue

                with SessionLocal() as db:
                    new_leads = (
                        db.query(Lead)
                        .filter(Lead.status == status_filter)
                        .order_by(Lead.created_at)
                        .all()
                    )
                    lead_ids = [lead.id for lead in new_leads]

                progress["leads_from_crawl"] = progress.get("leads_from_crawl", 0) + len(
                    lead_ids
                )
                progress["crawl_rounds"] = crawl_rounds
                sync_progress(current_step="crawling")
                logger.info("batch_post_crawl", new_leads=len(lead_ids), round=crawl_rounds)

                if not lead_ids:
                    break

            crawl_rounds = 0
            batch_total = len(lead_ids)
            progress["total"] = total_processed + batch_total
            sync_progress()

            for idx, lead_id in enumerate(lead_ids):
                if should_stop_operational_task(
                    task_id=task_id,
                    redis_key=BATCH_PIPELINE_REDIS_KEY,
                    treat_missing_legacy_as_stop=True,
                ):
                    return stop_pipeline()

                progress["processed"] = total_processed + idx
                progress["current_step"] = "enrichment"
                sync_progress(current_step="enrichment")

                try:
                    with SessionLocal() as db:
                        lead = db.get(Lead, lead_id)
                        if not lead:
                            continue

                        progress["current_lead"] = lead.business_name
                        sync_progress(current_step="enrichment")

                        enrich_lead(db, lead.id)

                        progress["current_step"] = "scoring"
                        sync_progress(current_step="scoring")
                        score_lead(db, lead.id)

                        progress["current_step"] = "analysis"
                        sync_progress(current_step="analysis")

                        db.refresh(lead)

                        analysis = run_lead_analysis_step(
                            db,
                            lead,
                            source_tag="batch_pipeline",
                        )
                        db.commit()

                        if analysis.quality == "high":
                            progress["current_step"] = "research"
                            sync_progress(current_step="research")
                            run_high_value_lane_inline(db, lead.id)

                            progress["current_step"] = "brief"
                            sync_progress(current_step="brief")

                        progress["current_step"] = "draft"
                        sync_progress(current_step="draft")
                        draft_result = run_draft_generation_step(db, lead.id)
                        if draft_result.status != "ok":
                            logger.info(
                                "batch_draft_step_non_ok",
                                lead=lead.business_name,
                                status=draft_result.status,
                                reason=draft_result.reason,
                            )

                        logger.info(
                            "batch_pipeline_lead_done",
                            lead=lead.business_name,
                            idx=total_processed + idx + 1,
                        )

                except Exception as exc:
                    total_errors += 1
                    progress["errors"] = total_errors
                    sync_progress()
                    logger.error(
                        "batch_pipeline_lead_error",
                        lead_id=str(lead_id),
                        error=str(exc),
                    )

            total_processed += batch_total

        progress["status"] = "done"
        progress["processed"] = total_processed
        progress["total"] = total_processed
        progress["current_lead"] = None
        progress["current_step"] = ""
        result = {
            "status": "done",
            "task_id": task_id,
            "total": total_processed,
            "errors": total_errors,
        }
        sync_progress(
            current_step="completed",
            status="succeeded",
            clear_error=True,
            finished=True,
            result=result,
            stop_requested=False,
        )
        logger.info(
            "batch_pipeline_done",
            total=total_processed,
            errors=total_errors,
            crawl_rounds=crawl_rounds,
        )
        return result

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
