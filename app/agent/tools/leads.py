"""Lead tools — search, detail, and count."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import LeadCreate
from app.services.leads.lead_service import (
    create_lead as _create_lead,
)
from app.services.leads.lead_service import (
    get_lead,
)
from app.services.leads.lead_service import (
    update_lead_status as _update_lead_status,
)


def search_leads(
    db: Session,
    *,
    query: str | None = None,
    status: str | None = None,
    city: str | None = None,
    industry: str | None = None,
    min_score: float | None = None,
    limit: int = 10,
) -> dict:
    """Search leads with filters."""
    lead_status = LeadStatus(status) if status else None
    # Build DB query with all filters pushed down
    stmt = select(Lead)
    count_stmt = select(func.count(Lead.id))

    if lead_status:
        stmt = stmt.where(Lead.status == lead_status)
        count_stmt = count_stmt.where(Lead.status == lead_status)
    if min_score is not None:
        stmt = stmt.where(Lead.score >= min_score)
        count_stmt = count_stmt.where(Lead.score >= min_score)
    if query:
        q_pattern = f"%{query}%"
        name_match = Lead.business_name.ilike(q_pattern)
        industry_match = Lead.industry.ilike(q_pattern)
        city_match = Lead.city.ilike(q_pattern)
        stmt = stmt.where(name_match | industry_match | city_match)
        count_stmt = count_stmt.where(name_match | industry_match | city_match)
    if city:
        stmt = stmt.where(Lead.city.ilike(f"%{city}%"))
        count_stmt = count_stmt.where(Lead.city.ilike(f"%{city}%"))
    if industry:
        stmt = stmt.where(Lead.industry.ilike(f"%{industry}%"))
        count_stmt = count_stmt.where(Lead.industry.ilike(f"%{industry}%"))

    total = db.execute(count_stmt).scalar() or 0
    leads = (
        db.execute(
            stmt.order_by(Lead.score.desc().nulls_last(), Lead.created_at.desc()).limit(
                min(limit, 50)
            )
        )
        .scalars()
        .all()
    )

    return {
        "total": total,
        "returned": len(leads),
        "leads": [
            {
                "id": str(l.id),
                "business_name": l.business_name,
                "industry": l.industry,
                "city": l.city,
                "status": l.status.value if l.status else None,
                "score": l.score,
                "email": l.email,
                "website_url": l.website_url,
                "llm_quality": l.llm_quality,
            }
            for l in leads
        ],
    }


def get_lead_detail(
    db: Session, *, lead_id: str | None = None, business_name: str | None = None
) -> dict:
    """Get detailed lead info by ID or business name."""
    lead = None
    if lead_id:
        try:
            lead = get_lead(db, uuid.UUID(lead_id))
        except ValueError:
            return {"error": "ID de lead inválido (debe ser UUID)"}
    elif business_name:
        safe_name = business_name.replace("%", r"\%").replace("_", r"\_")
        stmt = select(Lead).where(Lead.business_name.ilike(f"%{safe_name}%")).limit(1)
        lead = db.execute(stmt).scalar_one_or_none()

    if not lead:
        return {"error": "Lead no encontrado"}

    return {
        "id": str(lead.id),
        "business_name": lead.business_name,
        "industry": lead.industry,
        "city": lead.city,
        "zone": lead.zone,
        "status": lead.status.value if lead.status else None,
        "score": lead.score,
        "email": lead.email,
        "phone": lead.phone,
        "website_url": lead.website_url,
        "instagram_url": lead.instagram_url,
        "llm_summary": lead.llm_summary,
        "llm_quality": lead.llm_quality,
        "llm_suggested_angle": lead.llm_suggested_angle,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }


def count_leads_by_status(db: Session) -> dict:
    """Count leads grouped by status."""
    rows = db.execute(select(Lead.status, func.count()).group_by(Lead.status)).all()
    counts = {row[0].value: row[1] for row in rows}
    counts["total"] = sum(counts.values())
    return counts


registry.register(
    ToolDefinition(
        name="search_leads",
        description="Buscar leads con filtros opcionales (texto, estado, ciudad, industria, score mínimo)",
        parameters=[
            ToolParameter(
                "query", "string", "Texto de búsqueda (nombre, industria o ciudad)", required=False
            ),
            ToolParameter(
                "status",
                "string",
                "Filtrar por estado del lead",
                required=False,
                enum=[s.value for s in LeadStatus],
            ),
            ToolParameter("city", "string", "Filtrar por ciudad", required=False),
            ToolParameter("industry", "string", "Filtrar por industria/rubro", required=False),
            ToolParameter("min_score", "number", "Score mínimo", required=False),
            ToolParameter(
                "limit", "integer", "Cantidad máxima de resultados (default 10)", required=False
            ),
        ],
        category="leads",
        handler=search_leads,
    )
)

registry.register(
    ToolDefinition(
        name="get_lead_detail",
        description="Obtener información detallada de un lead por ID o nombre del negocio",
        parameters=[
            ToolParameter("lead_id", "string", "UUID del lead", required=False),
            ToolParameter(
                "business_name", "string", "Nombre del negocio (búsqueda parcial)", required=False
            ),
        ],
        category="leads",
        handler=get_lead_detail,
    )
)

registry.register(
    ToolDefinition(
        name="count_leads_by_status",
        description="Contar leads agrupados por estado (new, enriched, scored, etc.)",
        category="leads",
        handler=count_leads_by_status,
    )
)


def get_lead_journey(db: Session, *, lead_id: str) -> dict:
    """Get the full AI journey for a lead: pipeline context, corrections, delivery, investigation."""
    from app.models.investigation_thread import InvestigationThread
    from app.models.outreach_draft import OutreachDraft
    from app.models.review_correction import ReviewCorrection
    from app.models.task_tracking import PipelineRun

    try:
        lid = uuid.UUID(lead_id)
    except ValueError:
        return {"error": "ID de lead inválido"}

    lead = db.get(Lead, lid)
    if not lead:
        return {"error": "Lead no encontrado"}

    journey: dict = {
        "lead": lead.business_name,
        "score": lead.score,
        "quality": lead.llm_quality,
        "status": lead.status.value if lead.status else None,
    }

    # Pipeline context (latest run)
    run = (
        db.query(PipelineRun).filter_by(lead_id=lid).order_by(PipelineRun.created_at.desc()).first()
    )
    if run:
        journey["pipeline"] = {
            "status": run.status,
            "current_step": run.current_step,
            "context_keys": list((run.step_context_json or {}).keys()),
            "context": run.step_context_json,
        }

    # Investigation thread (Scout)
    thread = (
        db.query(InvestigationThread)
        .filter_by(lead_id=lid)
        .order_by(InvestigationThread.created_at.desc())
        .first()
    )
    if thread:
        journey["scout_investigation"] = {
            "pages_visited": thread.pages_visited_json,
            "findings": thread.findings_json,
            "loops_used": thread.loops_used,
            "duration_ms": thread.duration_ms,
        }

    # Review corrections
    corrections = (
        db.query(ReviewCorrection)
        .filter_by(lead_id=lid)
        .order_by(ReviewCorrection.created_at.desc())
        .limit(10)
        .all()
    )
    if corrections:
        journey["corrections"] = [
            {"category": c.category, "severity": c.severity, "issue": c.issue} for c in corrections
        ]

    # Outreach draft
    draft = (
        db.query(OutreachDraft)
        .filter_by(lead_id=lid)
        .order_by(OutreachDraft.created_at.desc())
        .first()
    )
    if draft:
        journey["draft"] = {
            "subject": draft.subject,
            "status": draft.status.value if hasattr(draft.status, "value") else str(draft.status),
            "channel": getattr(draft, "channel", None),
        }

    return journey


registry.register(
    ToolDefinition(
        name="get_lead_journey",
        description="Ver el viaje completo de un lead: pipeline, Scout, corrections, draft, delivery",
        parameters=[
            ToolParameter("lead_id", "string", "UUID del lead"),
        ],
        category="leads",
        handler=get_lead_journey,
    )
)


# ---------------------------------------------------------------------------
# create_lead
# ---------------------------------------------------------------------------


def create_lead(
    db: Session,
    *,
    business_name: str,
    industry: str | None = None,
    city: str | None = None,
    email: str | None = None,
    website_url: str | None = None,
    instagram_url: str | None = None,
    phone: str | None = None,
) -> dict:
    """Create a new lead."""
    try:
        lead = _create_lead(
            db,
            LeadCreate(
                business_name=business_name,
                industry=industry,
                city=city,
                email=email,
                website_url=website_url,
                instagram_url=instagram_url,
                phone=phone,
            ),
        )
    except ValueError as exc:
        return {"error": str(exc)}
    db.flush()
    return {
        "id": str(lead.id),
        "business_name": lead.business_name,
        "status": lead.status.value if lead.status else None,
        "dedup_hash": lead.dedup_hash,
    }


registry.register(
    ToolDefinition(
        name="create_lead",
        description=("Crear un nuevo lead en el sistema (requiere confirmación)"),
        parameters=[
            ToolParameter(
                "business_name",
                "string",
                "Nombre del negocio",
            ),
            ToolParameter(
                "industry",
                "string",
                "Industria o rubro",
                required=False,
            ),
            ToolParameter(
                "city",
                "string",
                "Ciudad",
                required=False,
            ),
            ToolParameter(
                "email",
                "string",
                "Email de contacto",
                required=False,
            ),
            ToolParameter(
                "website_url",
                "string",
                "URL del sitio web",
                required=False,
            ),
            ToolParameter(
                "instagram_url",
                "string",
                "URL de Instagram",
                required=False,
            ),
            ToolParameter(
                "phone",
                "string",
                "Teléfono de contacto",
                required=False,
            ),
        ],
        category="leads",
        requires_confirmation=True,
        handler=create_lead,
    )
)


# ---------------------------------------------------------------------------
# update_lead_status
# ---------------------------------------------------------------------------


def update_lead_status(db: Session, *, lead_id: str, status: str) -> dict:
    """Update a lead's status."""
    try:
        lid = uuid.UUID(lead_id)
    except ValueError:
        return {"error": "ID de lead inválido (debe ser UUID)"}

    lead = get_lead(db, lid)
    if not lead:
        return {"error": "Lead no encontrado"}

    old_status = lead.status.value if lead.status else None
    updated = _update_lead_status(db, lid, LeadStatus(status))
    if not updated:
        return {"error": "No se pudo actualizar el estado"}
    db.flush()
    return {
        "id": str(updated.id),
        "business_name": updated.business_name,
        "old_status": old_status,
        "new_status": updated.status.value,
    }


registry.register(
    ToolDefinition(
        name="update_lead_status",
        description=("Actualizar el estado de un lead (requiere confirmación)"),
        parameters=[
            ToolParameter("lead_id", "string", "UUID del lead"),
            ToolParameter(
                "status",
                "string",
                "Nuevo estado del lead",
                enum=[s.value for s in LeadStatus],
            ),
        ],
        category="leads",
        requires_confirmation=True,
        handler=update_lead_status,
    )
)
