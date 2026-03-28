"""Stats tools — dashboard metrics, pipeline breakdown, industry data."""

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.dashboard_service import (
    get_dashboard_stats as _get_stats,
    get_industry_breakdown as _get_industry,
    get_pipeline_breakdown as _get_pipeline,
)


def get_dashboard_stats(db: Session) -> dict:
    """Get aggregated dashboard statistics."""
    return _get_stats(db)


def get_pipeline_breakdown(db: Session) -> dict:
    """Get pipeline stage counts."""
    stages = _get_pipeline(db)
    return {"stages": stages}


def get_industry_breakdown(db: Session) -> dict:
    """Get lead breakdown by industry."""
    industries = _get_industry(db)
    return {"industries": industries}


registry.register(ToolDefinition(
    name="get_dashboard_stats",
    description=(
        "Obtener estadísticas generales del dashboard: total leads, contactados, "
        "respondidos, ganados, tasas de conversión, velocidad del pipeline"
    ),
    category="stats",
    handler=get_dashboard_stats,
))

registry.register(ToolDefinition(
    name="get_pipeline_breakdown",
    description="Obtener desglose del pipeline por etapas (nuevos, enriquecidos, calificados, etc.)",
    category="stats",
    handler=get_pipeline_breakdown,
))

registry.register(ToolDefinition(
    name="get_industry_breakdown",
    description="Obtener desglose de leads por industria/rubro con scores y tasas de conversión",
    category="stats",
    handler=get_industry_breakdown,
))
