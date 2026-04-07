"""Pipeline context service — accumulates step findings through the pipeline.

Each pipeline step writes its findings to PipelineRun.step_context_json.
Downstream steps (especially draft generation) read the full accumulated context
to produce informed, personalized output.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task_tracking import PipelineRun

logger = get_logger(__name__)


_MAX_STEP_BYTES = 2048
_MAX_TOTAL_BYTES = 16384


def append_step_context(
    db: Session,
    pipeline_run_id: uuid.UUID | str,
    step_name: str,
    context: dict,
) -> None:
    """Merge step findings into PipelineRun.step_context_json.

    Each step writes under its own key, so steps never overwrite each other.
    Enforces size limits: 2KB per step, 16KB total.
    """
    import json as _json

    run_id = uuid.UUID(str(pipeline_run_id))
    run = db.get(PipelineRun, run_id)
    if not run:
        logger.warning("pipeline_run_not_found", pipeline_run_id=str(run_id), step=step_name)
        return

    serialized = _json.dumps(context, default=str)
    if len(serialized) > _MAX_STEP_BYTES:
        logger.warning("step_context_too_large", step=step_name, size=len(serialized))
        context = {"truncated": True, "summary": serialized[:500]}

    existing = dict(run.step_context_json or {})
    existing[step_name] = context

    total = _json.dumps(existing, default=str)
    if len(total) > _MAX_TOTAL_BYTES:
        logger.error("total_context_too_large", step=step_name, size=len(total))
        return

    run.step_context_json = existing
    db.commit()

    logger.debug(
        "step_context_appended",
        pipeline_run_id=str(run_id),
        step=step_name,
        context_keys=list(existing.keys()),
    )


def get_step_context(db: Session, pipeline_run_id: uuid.UUID | str) -> dict:
    """Read full accumulated context for a pipeline run."""
    run_id = uuid.UUID(str(pipeline_run_id))
    run = db.get(PipelineRun, run_id)
    return dict(run.step_context_json or {}) if run else {}


def format_context_for_prompt(context: dict, max_chars: int = 2000) -> str:
    """Format pipeline context as a concise text block for LLM prompt injection.

    Summarizes each step's findings into a readable block that fits
    within a token budget (~500 tokens ≈ 2000 chars).
    """
    if not context:
        return ""

    parts = []

    if "enrichment" in context:
        e = context["enrichment"]
        signals = ", ".join(e.get("signals", []))
        parts.append(
            f"Enrichment: signals=[{signals}], email={'yes' if e.get('email_found') else 'no'}"
        )

    if "scoring" in context:
        s = context["scoring"]
        parts.append(f"Score: {s.get('score', '?')}/100")

    if "analysis" in context:
        a = context["analysis"]
        parts.append(f"Quality: {a.get('quality', '?')} — {a.get('reasoning', '')}")
        if a.get("suggested_angle"):
            parts.append(f"Angle: {a['suggested_angle']}")

    if "scout" in context:
        sc = context["scout"]
        findings = sc.get("findings", {})
        if isinstance(findings, dict):
            parts.append(
                f"Scout findings: {findings.get('opportunity', findings.get('summary', ''))}"
            )
        elif isinstance(findings, str):
            parts.append(f"Scout findings: {findings}")
        pages = sc.get("pages_visited", [])
        if pages:
            parts.append(f"Scout visited: {len(pages)} pages")

    if "research" in context:
        r = context["research"]
        if r.get("business_description"):
            parts.append(f"Research: {r['business_description']}")
        if r.get("whatsapp_detected"):
            parts.append("WhatsApp detected: yes")

    if "brief" in context:
        b = context["brief"]
        parts.append(
            f"Brief: opportunity={b.get('opportunity_score', '?')}, "
            f"budget={b.get('budget_tier', '?')}, "
            f"channel={b.get('recommended_contact_method', '?')}"
        )
        if b.get("recommended_angle"):
            parts.append(f"Brief angle: {b['recommended_angle']}")

    if "brief_review" in context:
        br = context["brief_review"]
        approved = br.get("approved")
        parts.append(f"Brief review: {'approved' if approved else 'needs revision'}")
        if br.get("verdict_reasoning"):
            parts.append(f"Review note: {br['verdict_reasoning']}")

    result = "\n".join(parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    return result
