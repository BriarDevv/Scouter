"""Settings tools — read and update operational settings."""

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.settings.operational_settings_service import get_cached_settings


# Whitelist of settings the agent can modify
_SAFE_SETTINGS = {
    "reply_assistant_enabled",
    "auto_classify_enabled",
    "reviewer_enabled",
    "mail_enabled",
    "telegram_agent_enabled",
    "whatsapp_agent_enabled",
    "whatsapp_outreach_enabled",
    "default_outreach_tone",
    "default_reply_tone",
    "default_closing_line",
}


def get_operational_settings(db: Session) -> dict:
    """Get current operational settings."""
    settings_obj = get_cached_settings(db)
    if not settings_obj:
        return {"error": "No hay configuración operacional guardada"}
    return settings_obj.to_dict() if hasattr(settings_obj, "to_dict") else {
        "id": str(settings_obj.id),
        "settings": settings_obj.settings_json if hasattr(settings_obj, "settings_json") else {},
    }


def update_setting(db: Session, *, key: str, value: str) -> dict:
    """Update a single operational setting."""
    if key not in _SAFE_SETTINGS:
        return {
            "error": f"No se puede modificar '{key}'. "
            f"Configuraciones permitidas: {sorted(_SAFE_SETTINGS)}",
        }

    settings_obj = get_cached_settings(db)
    if not settings_obj:
        return {"error": "No hay configuración operacional guardada"}

    # Convert string values to appropriate types
    if value.lower() in ("true", "false"):
        typed_value = value.lower() == "true"
    else:
        typed_value = value

    if hasattr(settings_obj, key):
        setattr(settings_obj, key, typed_value)
        db.commit()
        db.refresh(settings_obj)
        return {"key": key, "value": typed_value, "status": "updated"}

    return {"error": f"Campo '{key}' no encontrado en la configuración"}


registry.register(ToolDefinition(
    name="get_operational_settings",
    description="Ver la configuración operacional actual del sistema",
    category="settings",
    handler=get_operational_settings,
))

registry.register(ToolDefinition(
    name="update_setting",
    description="Modificar una configuración operacional (requiere confirmación)",
    parameters=[
        ToolParameter("key", "string", "Nombre de la configuración a cambiar",
                      enum=sorted(_SAFE_SETTINGS)),
        ToolParameter("value", "string", "Nuevo valor"),
    ],
    category="settings",
    requires_confirmation=True,
    handler=update_setting,
))
