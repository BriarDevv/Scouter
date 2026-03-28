"""Suppression tools — list, add, and remove suppression entries."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.schemas.suppression import SuppressionCreate
from app.services.suppression_service import (
    add_to_suppression_list,
    list_suppression as _list_suppression,
    remove_from_suppression as _remove_from_suppression,
)


# ---------------------------------------------------------------------------
# list_suppression
# ---------------------------------------------------------------------------


def list_suppression(db: Session, *, limit: int = 20) -> dict:
    """List suppression entries."""
    entries = _list_suppression(db, page=1, page_size=min(limit, 50))
    return {
        "count": len(entries),
        "entries": [
            {
                "id": str(e.id),
                "email": e.email,
                "domain": e.domain,
                "phone": e.phone,
                "reason": e.reason,
                "added_at": (
                    e.added_at.isoformat() if e.added_at else None
                ),
            }
            for e in entries
        ],
    }


registry.register(ToolDefinition(
    name="list_suppression",
    description="Listar las entradas de la lista de supresión",
    parameters=[
        ToolParameter(
            "limit", "integer",
            "Cantidad máxima de resultados (default 20)",
            required=False,
        ),
    ],
    category="suppression",
    handler=list_suppression,
))


# ---------------------------------------------------------------------------
# add_to_suppression
# ---------------------------------------------------------------------------


def add_to_suppression(
    db: Session,
    *,
    email: str | None = None,
    domain: str | None = None,
    reason: str | None = None,
) -> dict:
    """Add an email or domain to the suppression list."""
    if not email and not domain:
        return {
            "error": "Debe proporcionar al menos un email o dominio",
        }
    entry = add_to_suppression_list(
        db,
        SuppressionCreate(email=email, domain=domain, reason=reason),
    )
    return {
        "id": str(entry.id),
        "email": entry.email,
        "domain": entry.domain,
        "reason": entry.reason,
    }


registry.register(ToolDefinition(
    name="add_to_suppression",
    description=(
        "Agregar un email o dominio a la lista de supresión "
        "(requiere confirmación)"
    ),
    parameters=[
        ToolParameter(
            "email", "string",
            "Email a suprimir", required=False,
        ),
        ToolParameter(
            "domain", "string",
            "Dominio a suprimir", required=False,
        ),
        ToolParameter(
            "reason", "string",
            "Motivo de la supresión", required=False,
        ),
    ],
    category="suppression",
    requires_confirmation=True,
    handler=add_to_suppression,
))


# ---------------------------------------------------------------------------
# remove_from_suppression
# ---------------------------------------------------------------------------


def remove_from_suppression(db: Session, *, entry_id: str) -> dict:
    """Remove an entry from the suppression list."""
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        return {"error": "ID de entrada inválido (debe ser UUID)"}
    success = _remove_from_suppression(db, eid)
    return {"success": success}


registry.register(ToolDefinition(
    name="remove_from_suppression",
    description=(
        "Eliminar una entrada de la lista de supresión "
        "(requiere confirmación)"
    ),
    parameters=[
        ToolParameter(
            "entry_id", "string",
            "UUID de la entrada a eliminar",
        ),
    ],
    category="suppression",
    requires_confirmation=True,
    handler=remove_from_suppression,
))
