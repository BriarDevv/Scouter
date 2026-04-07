"""Dashboard domain — stats, health, leader views."""

from app.services.dashboard.dashboard_service import (
    get_dashboard_stats,
    get_pipeline_breakdown,
    get_time_series,
    get_industry_breakdown,
    get_city_breakdown,
)
from app.services.dashboard.health_service import get_system_health

__all__ = [
    "get_dashboard_stats",
    "get_pipeline_breakdown",
    "get_time_series",
    "get_industry_breakdown",
    "get_city_breakdown",
    "get_system_health",
]
