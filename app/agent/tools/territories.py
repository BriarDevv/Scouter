"""Territory tools — list and create territories."""

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.territory_service import (
    create_territory as _create,
    get_territory_with_stats,
    list_territories as _list,
)


def list_territories(db: Session) -> dict:
    """List all territories with stats."""
    territories = _list(db)
    return {
        "count": len(territories),
        "territories": [
            get_territory_with_stats(db, t) for t in territories
        ],
    }


def create_territory(
    db: Session,
    *,
    name: str,
    cities: str,
    description: str | None = None,
    color: str | None = None,
) -> dict:
    """Create a new territory."""
    from app.schemas.territory import TerritoryCreate

    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    data = TerritoryCreate(
        name=name,
        cities=city_list,
        description=description,
        color=color or "#8b5cf6",
    )
    territory = _create(db, data)
    if not territory:
        return {"error": "No se pudo crear el territorio"}
    return {
        "id": str(territory.id),
        "name": territory.name,
        "cities": territory.cities,
        "status": "created",
    }


registry.register(ToolDefinition(
    name="list_territories",
    description="Listar todos los territorios con estadísticas de leads",
    category="territories",
    handler=list_territories,
))

registry.register(ToolDefinition(
    name="create_territory",
    description="Crear un nuevo territorio geográfico (requiere confirmación)",
    parameters=[
        ToolParameter("name", "string", "Nombre del territorio"),
        ToolParameter("cities", "string", "Ciudades separadas por coma"),
        ToolParameter("description", "string", "Descripción opcional", required=False),
        ToolParameter("color", "string", "Color hex (default #8b5cf6)", required=False),
    ],
    category="territories",
    requires_confirmation=True,
    handler=create_territory,
))
