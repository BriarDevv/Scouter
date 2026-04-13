"""Review tools — LLM reviewer pass on leads and outreach drafts."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.reviews.review_service import (
    review_draft_with_reviewer as _review_draft,
)
from app.services.reviews.review_service import (
    review_lead_with_reviewer as _review_lead,
)


def review_lead(db: Session, *, lead_id: str) -> dict:
    """Run a reviewer analysis on a lead."""
    try:
        lid = uuid.UUID(lead_id)
    except ValueError:
        return {"error": f"lead_id inválido: {lead_id}"}

    result = _review_lead(db, lid)
    if result is None:
        return {"error": "No se pudo revisar el lead (reviewer desactivado o lead no encontrado)"}
    db.flush()
    return {
        "verdict": result["verdict"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "recommended_action": result["recommended_action"],
    }


def review_draft(db: Session, *, draft_id: str) -> dict:
    """Run a reviewer analysis on an outreach draft."""
    try:
        did = uuid.UUID(draft_id)
    except ValueError:
        return {"error": f"draft_id inválido: {draft_id}"}

    result = _review_draft(db, did)
    if result is None:
        return {"error": "No se pudo revisar el draft (reviewer desactivado o draft no encontrado)"}
    db.flush()
    return {
        "verdict": result["verdict"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "suggested_changes": result["suggested_changes"],
    }


registry.register(
    ToolDefinition(
        name="review_lead",
        description=(
            "Ejecutar una revisión con el modelo Reviewer sobre un lead: "
            "obtiene veredicto, confianza, razonamiento y acción recomendada"
        ),
        parameters=[
            ToolParameter("lead_id", "string", "UUID del lead a revisar"),
        ],
        category="reviews",
        handler=review_lead,
    )
)

registry.register(
    ToolDefinition(
        name="review_draft",
        description=(
            "Ejecutar una revisión con el modelo Reviewer sobre un borrador de outreach: "
            "obtiene veredicto, confianza, razonamiento y cambios sugeridos"
        ),
        parameters=[
            ToolParameter("draft_id", "string", "UUID del draft a revisar"),
        ],
        category="reviews",
        handler=review_draft,
    )
)
