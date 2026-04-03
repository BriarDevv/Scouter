"""Shared lead-pipeline step helpers.

These helpers deliberately centralize the business sequence shared by the
single-lead async pipeline and the batch inline pipeline without introducing a
new framework or changing operational tracking ownership.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.client import evaluate_lead_quality_structured, summarize_business
from app.llm.roles import LLMRole
from app.models.lead import Lead
from app.workflows.outreach_draft_generation import (
    OutreachDraftWorkflowResult,
    run_outreach_draft_automation,
    run_outreach_draft_generation_workflow,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class LeadAnalysisStepResult:
    summary: str
    quality: str
    reasoning: str
    suggested_angle: str


@dataclass(slots=True)
class HighValueLaneResult:
    research_completed: bool = False
    brief_generated: bool = False
    warnings: list[str] = field(default_factory=list)


def run_lead_analysis_step(
    db: Session,
    lead: Lead,
    *,
    source_tag: str,
    role: LLMRole = LLMRole.EXECUTOR,
) -> LeadAnalysisStepResult:
    """Run summary + quality evaluation and persist normalized lead fields."""
    summary = summarize_business(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        signals=list(lead.signals),
        role=role,
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
        role=role,
        target_type="lead",
        target_id=str(lead.id),
        tags={"workflow": source_tag},
    )
    evaluation_payload = evaluation.parsed

    reasoning = (
        evaluation_payload.reasoning
        if evaluation_payload
        else "LLM analysis unavailable"
    )
    suggested_angle = (
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
            source_tag=source_tag,
        )

    quality = raw_quality if raw_quality in ("high", "medium", "low") else "unknown"
    lead.llm_quality_assessment = reasoning
    lead.llm_suggested_angle = suggested_angle
    lead.llm_quality = quality

    return LeadAnalysisStepResult(
        summary=summary,
        quality=quality,
        reasoning=reasoning,
        suggested_angle=suggested_angle,
    )


def run_high_value_lane_inline(db: Session, lead_id: uuid.UUID) -> HighValueLaneResult:
    """Run the synchronous HIGH-lane follow-ups used by the batch workflow.

    Batch intentionally stays inline here so it can preserve aggregate progress,
    stop handling, and per-lead error tolerance. Single-lead flow still uses the
    async research/brief/review tasks.
    """
    result = HighValueLaneResult()

    try:
        from app.services.research.research_service import run_research

        report = run_research(db, lead_id)
        result.research_completed = bool(report and report.status.value == "completed")
    except Exception as exc:
        result.warnings.append(f"research:{exc}")
        logger.warning(
            "lead_high_value_lane_research_failed",
            lead_id=str(lead_id),
            error=str(exc),
        )

    try:
        from app.services.research.brief_service import generate_brief

        brief = generate_brief(db, lead_id)
        result.brief_generated = bool(brief and brief.status.value == "generated")
    except Exception as exc:
        result.warnings.append(f"brief:{exc}")
        logger.warning(
            "lead_high_value_lane_brief_failed",
            lead_id=str(lead_id),
            error=str(exc),
        )

    return result


def run_draft_generation_step(
    db: Session,
    lead_id: uuid.UUID,
    *,
    apply_automation: bool = True,
    pipeline_context_text: str = "",
) -> OutreachDraftWorkflowResult:
    """Run the canonical draft generation workflow and optional automation."""
    workflow_result = run_outreach_draft_generation_workflow(
        db, lead_id, pipeline_context_text=pipeline_context_text,
    )
    if (
        apply_automation
        and workflow_result.status == "ok"
        and workflow_result.draft_id
    ):
        run_outreach_draft_automation(db, uuid.UUID(workflow_result.draft_id))
    return workflow_result
