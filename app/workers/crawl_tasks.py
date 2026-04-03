"""Celery tasks for territory crawling."""

import uuid

from app.core.logging import get_logger
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
    max_retries=0,
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
