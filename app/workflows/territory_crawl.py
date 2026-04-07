"""Workflow helpers for territory crawl orchestration."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from structlog.contextvars import bound_contextvars

from app.core.logging import get_logger
from app.crawlers.google_maps_crawler import GoogleMapsCrawler
from app.db.session import SessionLocal
from app.models.lead import Lead
from app.models.lead_source import LeadSource, SourceType
from app.models.territory import Territory
from app.schemas.lead import LeadCreate
from app.services.leads.lead_service import _compute_dedup_hash, create_lead
from app.services.pipeline.operational_task_service import (
    build_territory_crawl_progress,
    mirror_territory_crawl_state,
    persist_operational_task_state,
    should_stop_operational_task,
    territory_crawl_redis_key,
)
from app.services.pipeline.task_tracking_service import mark_task_running

logger = get_logger(__name__)


def run_territory_crawl_workflow(
    *,
    task_id: str,
    territory_id: str,
    categories: list[str] | None = None,
    only_without_website: bool = False,
    max_results_per_category: int = 20,
    target_leads: int = 50,
    correlation_id: str | None = None,
    queue: str = "default",
) -> dict[str, object]:
    """Crawl all cities in a territory using canonical TaskRun state."""
    redis_key = territory_crawl_redis_key(territory_id)
    progress = build_territory_crawl_progress(task_id=task_id)
    progress["current_step"] = "crawl_init"

    def sync_progress(
        *,
        current_step: str | None = None,
        status: str | None = None,
        error: str | None = None,
        clear_error: bool = False,
        finished: bool = False,
        result: dict | None = None,
        stop_requested: bool | None = None,
        mirror_payload: dict | None = None,
        mirror: bool = True,
    ) -> None:
        if current_step is not None:
            progress["current_step"] = current_step
        if mirror:
            mirror_territory_crawl_state(territory_id, mirror_payload or progress)
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

    with bound_contextvars(
        task_id=task_id,
        correlation_id=correlation_id,
        current_step="crawl_init",
    ):
        with SessionLocal() as db:
            mark_task_running(
                db,
                task_id=task_id,
                task_name="task_crawl_territory",
                queue=queue,
                correlation_id=correlation_id,
                scope_key=territory_id,
                current_step="crawl_init",
            )
            db.commit()

        try:
            with SessionLocal() as db:
                territory = db.get(Territory, uuid.UUID(territory_id))
                if not territory:
                    error = "Territorio no encontrado"
                    sync_progress(
                        status="failed",
                        error=error,
                        finished=True,
                        mirror_payload={"status": "error", "task_id": task_id, "error": error},
                    )
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "territory_id": territory_id,
                        "error": error,
                    }

                cities = list(territory.cities or [])
                territory_name = territory.name
                if not cities:
                    error = "El territorio no tiene ciudades"
                    sync_progress(
                        status="failed",
                        error=error,
                        finished=True,
                        mirror_payload={"status": "error", "task_id": task_id, "error": error},
                    )
                    return {
                        "status": "error",
                        "task_id": task_id,
                        "territory_id": territory_id,
                        "error": error,
                    }

                source = db.query(LeadSource).filter(LeadSource.name == "google_maps").first()
                if not source:
                    source = LeadSource(
                        name="google_maps",
                        source_type=SourceType.CRAWLER,
                        description="Google Maps Places API",
                    )
                    db.add(source)
                    db.commit()
                    db.refresh(source)
                source_id = source.id

            progress["territory"] = territory_name
            progress["total_cities"] = len(cities)
            sync_progress(current_step="crawl_init", clear_error=True)

            crawler = GoogleMapsCrawler()
            total_found = 0
            total_created = 0
            total_dup = 0

            for idx, city in enumerate(cities):
                if should_stop_operational_task(
                    task_id=task_id,
                    redis_key=redis_key,
                    treat_missing_legacy_as_stop=True,
                ):
                    progress["status"] = "stopped"
                    sync_progress(status="stopped", finished=True)
                    logger.info("territory_crawl_stopped_by_user", territory=territory_name)
                    return {"status": "stopped", "task_id": task_id, "territory": territory_name}

                progress["current_city_idx"] = idx + 1
                progress["current_city"] = city
                sync_progress(current_step="crawling")

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
                            dedup = _compute_dedup_hash(
                                raw.business_name,
                                raw.city,
                                raw.website_url,
                            )
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
                            db.commit()
                            total_created += 1
                        except Exception as exc:
                            logger.debug("lead_create_skipped", error=str(exc), exc_info=True)
                            total_dup += 1

                progress["leads_found"] = total_found
                progress["leads_created"] = total_created
                progress["leads_skipped"] = total_dup
                sync_progress(current_step="crawling")

            progress["status"] = "done"
            result = {
                "status": "done",
                "task_id": task_id,
                "territory": territory_name,
                "found": total_found,
                "created": total_created,
                "skipped": total_dup,
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
                "territory_crawl_done",
                territory=territory_name,
                cities=len(cities),
                found=total_found,
                created=total_created,
                skipped=total_dup,
            )
            return result
        except Exception as exc:
            sync_progress(
                status="failed",
                error=str(exc),
                finished=True,
                mirror_payload={"status": "error", "task_id": task_id, "error": str(exc)},
            )
            logger.error("territory_crawl_error", territory_id=territory_id, error=str(exc))
            raise
