"""Outreach tools — draft management."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.outreach_service import (
    get_draft,
    list_drafts as _list_drafts,
    review_draft,
)


def list_drafts(
    db: Session, *, status: str | None = None, limit: int = 10
) -> dict:
    """List outreach drafts with optional status filter."""
    from app.models.outreach import DraftStatus

    draft_status = DraftStatus(status) if status else None
    drafts = _list_drafts(db, status=draft_status, page_size=min(limit, 50))
    return {
        "count": len(drafts),
        "drafts": [
            {
                "id": str(d.id),
                "lead_id": str(d.lead_id),
                "subject": d.subject,
                "status": d.status.value if d.status else None,
                "generated_at": d.generated_at.isoformat() if d.generated_at else None,
            }
            for d in drafts
        ],
    }


def generate_draft(db: Session, *, lead_id: str) -> dict:
    """Generate an outreach draft for a lead."""
    from app.services.outreach_service import generate_outreach_draft

    draft = generate_outreach_draft(db, uuid.UUID(lead_id))
    if not draft:
        return {"error": "No se pudo generar el borrador (lead no encontrado o sin email)"}
    return {
        "id": str(draft.id),
        "subject": draft.subject,
        "body": draft.body,
        "status": draft.status.value,
    }


def approve_draft(db: Session, *, draft_id: str) -> dict:
    """Approve an outreach draft."""
    draft = review_draft(db, uuid.UUID(draft_id), approved=True)
    if not draft:
        return {"error": "Borrador no encontrado"}
    return {"id": str(draft.id), "status": draft.status.value}


def reject_draft(
    db: Session, *, draft_id: str, reason: str | None = None
) -> dict:
    """Reject an outreach draft."""
    draft = review_draft(db, uuid.UUID(draft_id), approved=False, feedback=reason)
    if not draft:
        return {"error": "Borrador no encontrado"}
    return {"id": str(draft.id), "status": draft.status.value}


registry.register(ToolDefinition(
    name="list_drafts",
    description="Listar borradores de outreach con filtro de estado opcional",
    parameters=[
        ToolParameter("status", "string", "Filtrar por estado", required=False,
                      enum=["pending_review", "approved", "rejected", "sent"]),
        ToolParameter("limit", "integer", "Cantidad máxima (default 10)", required=False),
    ],
    category="outreach",
    handler=list_drafts,
))

registry.register(ToolDefinition(
    name="generate_draft",
    description="Generar un borrador de email de outreach para un lead (requiere confirmación)",
    parameters=[
        ToolParameter("lead_id", "string", "UUID del lead"),
    ],
    category="outreach",
    requires_confirmation=True,
    handler=generate_draft,
))

registry.register(ToolDefinition(
    name="approve_draft",
    description="Aprobar un borrador de outreach para envío (requiere confirmación)",
    parameters=[
        ToolParameter("draft_id", "string", "UUID del borrador"),
    ],
    category="outreach",
    requires_confirmation=True,
    handler=approve_draft,
))

registry.register(ToolDefinition(
    name="reject_draft",
    description="Rechazar un borrador de outreach (requiere confirmación)",
    parameters=[
        ToolParameter("draft_id", "string", "UUID del borrador"),
        ToolParameter("reason", "string", "Motivo del rechazo", required=False),
    ],
    category="outreach",
    requires_confirmation=True,
    handler=reject_draft,
))
