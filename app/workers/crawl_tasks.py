"""Celery tasks for territory crawling."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app
from app.workflows.territory_crawl import run_territory_crawl_workflow

logger = get_logger(__name__)


def _queue_name(request, fallback: str) -> str:
    delivery_info = getattr(request, "delivery_info", None) or {}
    return delivery_info.get("routing_key") or delivery_info.get("queue") or fallback


def _request_task_id(request) -> str:
    request_id = getattr(request, "id", None)
    return str(request_id or uuid.uuid4())


@celery_app.task(
    name="app.workers.tasks.task_crawl_territory",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def task_crawl_territory(
    self,
    territory_id: str,
    categories: list[str] | None = None,
    only_without_website: bool = False,
    max_results_per_category: int = 20,
    target_leads: int = 50,
    correlation_id: str | None = None,
):
    """Thin Celery wrapper around the territory crawl workflow."""
    task_id = _request_task_id(self.request)
    queue = _queue_name(self.request, "default")
    try:
        return run_territory_crawl_workflow(
            task_id=task_id,
            territory_id=territory_id,
            categories=categories,
            only_without_website=only_without_website,
            max_results_per_category=max_results_per_category,
            target_leads=target_leads,
            correlation_id=correlation_id,
            queue=queue,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(
    name="app.workers.crawl_tasks.task_scheduled_crawl",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def task_scheduled_crawl(self):
    """Celery Beat task: crawl all active territories on schedule."""
    from app.models.territory import Territory

    try:
        with SessionLocal() as db:
            territories = (
                db.query(Territory)
                .filter(
                    Territory.is_active == True,  # noqa: E712
                    Territory.is_saturated == False,  # noqa: E712
                    or_(
                        Territory.last_crawled_at == None,  # noqa: E711
                        Territory.last_crawled_at < datetime.now(UTC) - timedelta(days=3),
                    ),
                )
                .all()
            )
            if not territories:
                logger.info("scheduled_crawl_no_active_territories")
                return {"status": "skipped", "reason": "no_active_territories"}

            dispatched = 0
            for t in territories:
                try:
                    task_crawl_territory.delay(str(t.id))
                    dispatched += 1
                except Exception as exc:
                    logger.warning(
                        "scheduled_crawl_dispatch_failed",
                        territory_id=str(t.id),
                        error=str(exc),
                    )

            logger.info("scheduled_crawl_dispatched", count=dispatched)
            return {"status": "ok", "territories_dispatched": dispatched}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc
