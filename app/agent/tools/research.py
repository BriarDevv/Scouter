"""Research & dossier tools — investigate leads and get dossier data."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry


def get_lead_dossier(db: Session, *, lead_id: str) -> dict:
    """Get the research dossier for a lead."""
    from app.models.research_report import LeadResearchReport

    report = db.query(LeadResearchReport).filter_by(
        lead_id=uuid.UUID(lead_id)
    ).first()
    if not report:
        return {"status": "not_found", "lead_id": lead_id}

    return {
        "id": str(report.id),
        "lead_id": lead_id,
        "status": report.status.value if report.status else None,
        "website_exists": report.website_exists,
        "website_confidence": (
            report.website_confidence.value if report.website_confidence else None
        ),
        "instagram_exists": report.instagram_exists,
        "instagram_confidence": (
            report.instagram_confidence.value if report.instagram_confidence else None
        ),
        "whatsapp_detected": report.whatsapp_detected,
        "whatsapp_confidence": (
            report.whatsapp_confidence.value if report.whatsapp_confidence else None
        ),
        "business_description": report.business_description,
        "detected_signals": report.detected_signals_json,
        "html_metadata": report.html_metadata_json,
        "research_duration_ms": report.research_duration_ms,
        "error": report.error,
    }


def run_lead_research(db: Session, *, lead_id: str) -> dict:
    """Run research/investigation on a lead."""
    from app.services.research.research_service import run_research

    report = run_research(db, uuid.UUID(lead_id))
    if not report:
        return {"status": "not_found", "lead_id": lead_id}
    return {
        "status": report.status.value if report.status else "unknown",
        "lead_id": lead_id,
        "signals_count": len(report.detected_signals_json or []),
    }


def get_commercial_brief(db: Session, *, lead_id: str) -> dict:
    """Get the commercial brief for a lead."""
    from app.models.commercial_brief import CommercialBrief

    brief = db.query(CommercialBrief).filter_by(
        lead_id=uuid.UUID(lead_id)
    ).first()
    if not brief:
        return {"status": "not_found", "lead_id": lead_id}

    return {
        "id": str(brief.id),
        "lead_id": lead_id,
        "status": brief.status.value if brief.status else None,
        "opportunity_score": brief.opportunity_score,
        "budget_tier": brief.budget_tier.value if brief.budget_tier else None,
        "estimated_budget_min": brief.estimated_budget_min,
        "estimated_budget_max": brief.estimated_budget_max,
        "estimated_scope": (
            brief.estimated_scope.value if brief.estimated_scope else None
        ),
        "recommended_contact_method": (
            brief.recommended_contact_method.value
            if brief.recommended_contact_method else None
        ),
        "should_call": brief.should_call.value if brief.should_call else None,
        "call_reason": brief.call_reason,
        "why_this_lead_matters": brief.why_this_lead_matters,
        "recommended_angle": brief.recommended_angle,
        "demo_recommended": brief.demo_recommended,
        "contact_priority": (
            brief.contact_priority.value if brief.contact_priority else None
        ),
    }


def generate_lead_brief(db: Session, *, lead_id: str) -> dict:
    """Generate a commercial brief for a lead."""
    from app.services.research.brief_service import generate_brief

    brief = generate_brief(db, uuid.UUID(lead_id))
    if not brief:
        return {"status": "not_found", "lead_id": lead_id}
    return {
        "status": brief.status.value if brief.status else "unknown",
        "lead_id": lead_id,
        "opportunity_score": brief.opportunity_score,
        "budget_tier": brief.budget_tier.value if brief.budget_tier else None,
    }


def export_leads_data(db: Session, *, format: str = "csv") -> dict:
    """Export leads data. Returns a message about the export."""
    return {
        "message": f"Usa el endpoint GET /api/v1/leads/export?format={format} "
        "para descargar los datos.",
        "format": format,
        "available_formats": ["csv", "json", "xlsx"],
    }


# ── Tool registration ────────────────────────────────────────────────

registry.register(ToolDefinition(
    name="get_lead_dossier",
    description="Get the research dossier/report for a lead",
    handler=get_lead_dossier,
    parameters=[
        ToolParameter(name="lead_id", type="string", description="Lead UUID", required=True),
    ],
))

registry.register(ToolDefinition(
    name="run_lead_research",
    description="Run digital research/investigation on a lead",
    handler=run_lead_research,
    requires_confirmation=True,
    parameters=[
        ToolParameter(name="lead_id", type="string", description="Lead UUID", required=True),
    ],
))

registry.register(ToolDefinition(
    name="get_commercial_brief",
    description="Get the commercial brief for a lead",
    handler=get_commercial_brief,
    parameters=[
        ToolParameter(name="lead_id", type="string", description="Lead UUID", required=True),
    ],
))

registry.register(ToolDefinition(
    name="generate_commercial_brief",
    description="Generate a commercial brief with budget and contact recommendation",
    handler=generate_lead_brief,
    requires_confirmation=True,
    parameters=[
        ToolParameter(name="lead_id", type="string", description="Lead UUID", required=True),
    ],
))

registry.register(ToolDefinition(
    name="export_leads",
    description="Export leads data as CSV, JSON, or XLSX",
    handler=export_leads_data,
    parameters=[
        ToolParameter(
            name="format", type="string", description="Export format",
            required=False, enum=["csv", "json", "xlsx"],
        ),
    ],
))


def get_investigation_thread(db: Session, *, lead_id: str) -> dict:
    """Get Scout investigation details for a lead."""
    from app.models.investigation_thread import InvestigationThread

    thread = (
        db.query(InvestigationThread)
        .filter_by(lead_id=uuid.UUID(lead_id))
        .order_by(InvestigationThread.created_at.desc())
        .first()
    )
    if not thread:
        return {"status": "not_found", "lead_id": lead_id}

    return {
        "lead_id": lead_id,
        "agent_model": thread.agent_model,
        "pages_visited": thread.pages_visited_json,
        "findings": thread.findings_json,
        "tool_calls": thread.tool_calls_json,
        "loops_used": thread.loops_used,
        "duration_ms": thread.duration_ms,
        "error": thread.error,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
    }


def trigger_scout_investigation(db: Session, *, lead_id: str) -> dict:
    """Trigger a deep Scout investigation (Playwright + LLM) for a lead."""
    from app.workers.research_tasks import task_research_lead

    task = task_research_lead.delay(lead_id)
    return {
        "status": "queued",
        "lead_id": lead_id,
        "task_id": str(task.id),
        "message": f"Investigación Scout disparada para lead {lead_id}",
    }


registry.register(ToolDefinition(
    name="get_investigation_thread",
    description="Ver detalles de investigación de Scout: páginas visitadas, findings, tool calls",
    handler=get_investigation_thread,
    parameters=[
        ToolParameter(name="lead_id", type="string", description="Lead UUID", required=True),
    ],
    category="research",
))

registry.register(ToolDefinition(
    name="trigger_scout_investigation",
    description="Disparar investigación profunda de Scout (Playwright + IA) para un lead",
    handler=trigger_scout_investigation,
    requires_confirmation=True,
    parameters=[
        ToolParameter(name="lead_id", type="string", description="Lead UUID", required=True),
    ],
    category="research",
))
