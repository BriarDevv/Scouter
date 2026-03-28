"""Lead tools — search, detail, and count."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.models.lead import Lead, LeadStatus
from app.services.lead_service import get_lead, list_leads


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
    leads, total = list_leads(
        db, page=1, page_size=min(limit, 50),
        status=lead_status, min_score=min_score,
    )

    # Apply text/city/industry filters in-memory (simple for now)
    if query:
        q = query.lower()
        leads = [
            l for l in leads
            if q in (l.business_name or "").lower()
            or q in (l.industry or "").lower()
            or q in (l.city or "").lower()
        ]
    if city:
        c = city.lower()
        leads = [l for l in leads if c in (l.city or "").lower()]
    if industry:
        ind = industry.lower()
        leads = [l for l in leads if ind in (l.industry or "").lower()]

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
        stmt = select(Lead).where(
            Lead.business_name.ilike(f"%{business_name}%")
        ).limit(1)
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
    rows = db.execute(
        select(Lead.status, func.count()).group_by(Lead.status)
    ).all()
    counts = {row[0].value: row[1] for row in rows}
    counts["total"] = sum(counts.values())
    return counts


registry.register(ToolDefinition(
    name="search_leads",
    description="Buscar leads con filtros opcionales (texto, estado, ciudad, industria, score mínimo)",
    parameters=[
        ToolParameter("query", "string", "Texto de búsqueda (nombre, industria o ciudad)", required=False),
        ToolParameter("status", "string", "Filtrar por estado del lead", required=False,
                      enum=[s.value for s in LeadStatus]),
        ToolParameter("city", "string", "Filtrar por ciudad", required=False),
        ToolParameter("industry", "string", "Filtrar por industria/rubro", required=False),
        ToolParameter("min_score", "number", "Score mínimo", required=False),
        ToolParameter("limit", "integer", "Cantidad máxima de resultados (default 10)", required=False),
    ],
    category="leads",
    handler=search_leads,
))

registry.register(ToolDefinition(
    name="get_lead_detail",
    description="Obtener información detallada de un lead por ID o nombre del negocio",
    parameters=[
        ToolParameter("lead_id", "string", "UUID del lead", required=False),
        ToolParameter("business_name", "string", "Nombre del negocio (búsqueda parcial)", required=False),
    ],
    category="leads",
    handler=get_lead_detail,
))

registry.register(ToolDefinition(
    name="count_leads_by_status",
    description="Contar leads agrupados por estado (new, enriched, scored, etc.)",
    category="leads",
    handler=count_leads_by_status,
))
