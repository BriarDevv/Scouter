"""Stats tools — dashboard metrics, pipeline breakdown, industry data."""

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.dashboard.dashboard_service import (
    get_city_breakdown as _get_cities,
)
from app.services.dashboard.dashboard_service import (
    get_dashboard_stats as _get_stats,
)
from app.services.dashboard.dashboard_service import (
    get_industry_breakdown as _get_industry,
)
from app.services.dashboard.dashboard_service import (
    get_pipeline_breakdown as _get_pipeline,
)
from app.services.dashboard.dashboard_service import (
    get_source_performance as _get_sources,
)
from app.services.dashboard.dashboard_service import (
    get_time_series as _get_time_series,
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


def get_city_breakdown(db: Session) -> dict:
    """Get lead breakdown by city."""
    result = _get_cities(db)
    return {"cities": result}


def get_source_performance(db: Session) -> dict:
    """Get lead source performance metrics."""
    result = _get_sources(db)
    return {"sources": result}


def get_time_series(db: Session, *, days: int = 30) -> dict:
    """Get time-series data for leads, outreach, replies, and conversions."""
    result = _get_time_series(db, days=days)
    return {"days": days, "series": result}


registry.register(
    ToolDefinition(
        name="get_dashboard_stats",
        description=(
            "Obtener estadísticas generales del dashboard: total leads, contactados, "
            "respondidos, ganados, tasas de conversión, velocidad del pipeline"
        ),
        category="stats",
        handler=get_dashboard_stats,
    )
)

registry.register(
    ToolDefinition(
        name="get_pipeline_breakdown",
        description=(
            "Obtener desglose del pipeline por etapas (nuevos, enriquecidos, calificados, etc.)"
        ),
        category="stats",
        handler=get_pipeline_breakdown,
    )
)

registry.register(
    ToolDefinition(
        name="get_industry_breakdown",
        description=(
            "Obtener desglose de leads por industria/rubro con scores y tasas de conversión"
        ),
        category="stats",
        handler=get_industry_breakdown,
    )
)

registry.register(
    ToolDefinition(
        name="get_city_breakdown",
        description="Obtener desglose de leads por ciudad con scores y tasas de respuesta",
        category="stats",
        handler=get_city_breakdown,
    )
)

registry.register(
    ToolDefinition(
        name="get_source_performance",
        description=(
            "Obtener rendimiento por fuente de leads: cantidad, score promedio, "
            "tasa de respuesta y conversión"
        ),
        category="stats",
        handler=get_source_performance,
    )
)

registry.register(
    ToolDefinition(
        name="get_time_series",
        description=(
            "Obtener serie temporal de leads, outreach, respuestas y conversiones "
            "para los últimos N días"
        ),
        parameters=[
            ToolParameter(
                "days",
                "integer",
                "Cantidad de días a incluir (default 30)",
                required=False,
            ),
        ],
        category="stats",
        handler=get_time_series,
    )
)
