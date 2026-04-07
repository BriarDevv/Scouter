"""System tools — health check and current time."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, registry
from app.services.dashboard.health_service import get_system_health


def health_check(db: Session) -> dict:
    """Run system health check."""
    return get_system_health(db)


def get_current_time() -> dict:
    """Get current server time in Buenos Aires timezone."""
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    return {
        "datetime": now.isoformat(),
        "date": now.date().isoformat(),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
    }


registry.register(
    ToolDefinition(
        name="health_check",
        description="Verificar el estado de salud del sistema (base de datos, Redis, Ollama, Celery)",
        category="system",
        handler=health_check,
    )
)

registry.register(
    ToolDefinition(
        name="get_current_time",
        description="Obtener la fecha y hora actual del servidor",
        category="system",
        handler=get_current_time,
    )
)
