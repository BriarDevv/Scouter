"""Territory tools — list, create, update, and delete territories."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.territory_service import (
    create_territory as _create,
)
from app.services.territory_service import (
    delete_territory as _delete,
)
from app.services.territory_service import (
    get_territory_with_stats,
)
from app.services.territory_service import (
    list_territories as _list,
)
from app.services.territory_service import (
    update_territory as _update,
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


def update_territory(
    db: Session,
    *,
    territory_id: str,
    name: str | None = None,
    cities: str | None = None,
    description: str | None = None,
    color: str | None = None,
    is_active: str | None = None,
) -> dict:
    """Update an existing territory."""
    from app.schemas.territory import TerritoryUpdate

    try:
        tid = uuid.UUID(territory_id)
    except ValueError:
        return {"error": f"territory_id inválido: {territory_id}"}

    kwargs: dict = {}
    if name is not None:
        kwargs["name"] = name
    if cities is not None:
        kwargs["cities"] = [c.strip() for c in cities.split(",") if c.strip()]
    if description is not None:
        kwargs["description"] = description
    if color is not None:
        kwargs["color"] = color
    if is_active is not None:
        kwargs["is_active"] = str(is_active).lower() in ("true", "1", "si", "sí")

    territory = _update(db, tid, TerritoryUpdate(**kwargs))
    if territory is None:
        return {"error": f"Territorio {territory_id} no encontrado"}
    return {
        "id": str(territory.id),
        "name": territory.name,
        "cities": territory.cities,
        "status": "updated",
    }


def delete_territory(db: Session, *, territory_id: str) -> dict:
    """Delete a territory by ID."""
    try:
        tid = uuid.UUID(territory_id)
    except ValueError:
        return {"error": f"territory_id inválido: {territory_id}"}

    result = _delete(db, tid)
    return {"success": result}


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

registry.register(ToolDefinition(
    name="update_territory",
    description="Actualizar un territorio existente (requiere confirmación)",
    parameters=[
        ToolParameter("territory_id", "string", "UUID del territorio"),
        ToolParameter("name", "string", "Nuevo nombre", required=False),
        ToolParameter("cities", "string", "Ciudades separadas por coma", required=False),
        ToolParameter(
            "description", "string", "Nueva descripción", required=False,
        ),
        ToolParameter("color", "string", "Nuevo color hex", required=False),
        ToolParameter(
            "is_active", "string",
            "Activar/desactivar territorio (true/false)",
            required=False,
        ),
    ],
    category="territories",
    requires_confirmation=True,
    handler=update_territory,
))

registry.register(ToolDefinition(
    name="delete_territory",
    description="Eliminar un territorio por ID (requiere confirmación)",
    parameters=[
        ToolParameter("territory_id", "string", "UUID del territorio a eliminar"),
    ],
    category="territories",
    requires_confirmation=True,
    handler=delete_territory,
))
