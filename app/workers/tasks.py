"""Celery tasks for async processing of leads."""

import uuid

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.llm.client import evaluate_lead_quality, summarize_business
from app.services.enrichment_service import enrich_lead
from app.services.outreach_service import generate_outreach_draft
from app.services.scoring_service import score_lead
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def task_enrich_lead(self, lead_id: str) -> dict:
    """Async task: enrich a lead with website analysis and signals."""
    try:
        with SessionLocal() as db:
            lead = enrich_lead(db, uuid.UUID(lead_id))
            if lead:
                return {"status": "ok", "lead_id": lead_id, "signals": len(lead.signals)}
            return {"status": "not_found", "lead_id": lead_id}
    except Exception as exc:
        logger.error("task_enrich_failed", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def task_score_lead(self, lead_id: str) -> dict:
    """Async task: score a lead based on signals."""
    try:
        with SessionLocal() as db:
            lead = score_lead(db, uuid.UUID(lead_id))
            if lead:
                return {"status": "ok", "lead_id": lead_id, "score": lead.score}
            return {"status": "not_found", "lead_id": lead_id}
    except Exception as exc:
        logger.error("task_score_failed", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def task_analyze_lead(self, lead_id: str) -> dict:
    """Async task: run LLM analysis (summary + quality evaluation) on a lead."""
    try:
        with SessionLocal() as db:
            from app.models.lead import Lead

            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                return {"status": "not_found", "lead_id": lead_id}

            # Summarize
            summary = summarize_business(
                business_name=lead.business_name,
                industry=lead.industry,
                city=lead.city,
                website_url=lead.website_url,
                instagram_url=lead.instagram_url,
                signals=list(lead.signals),
            )
            lead.llm_summary = summary

            # Evaluate quality
            evaluation = evaluate_lead_quality(
                business_name=lead.business_name,
                industry=lead.industry,
                city=lead.city,
                website_url=lead.website_url,
                instagram_url=lead.instagram_url,
                signals=list(lead.signals),
                score=lead.score,
            )
            lead.llm_quality_assessment = evaluation["reasoning"]
            lead.llm_suggested_angle = evaluation["suggested_angle"]

            db.commit()
            return {"status": "ok", "lead_id": lead_id, "quality": evaluation["quality"]}
    except Exception as exc:
        logger.error("task_analyze_failed", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def task_generate_draft(self, lead_id: str) -> dict:
    """Async task: generate outreach email draft."""
    try:
        with SessionLocal() as db:
            draft = generate_outreach_draft(db, uuid.UUID(lead_id))
            if draft:
                return {"status": "ok", "lead_id": lead_id, "draft_id": str(draft.id)}
            return {"status": "failed", "lead_id": lead_id}
    except Exception as exc:
        logger.error("task_generate_draft_failed", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task
def task_full_pipeline(lead_id: str) -> dict:
    """Run the full pipeline: enrich -> score -> analyze -> generate draft."""
    from celery import chain

    pipeline = chain(
        task_enrich_lead.s(lead_id),
        task_score_lead.si(lead_id),
        task_analyze_lead.si(lead_id),
        task_generate_draft.si(lead_id),
    )
    result = pipeline.apply_async()
    return {"status": "pipeline_started", "lead_id": lead_id, "task_id": str(result.id)}
