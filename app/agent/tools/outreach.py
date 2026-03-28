"""Outreach tools — draft management."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.models.outreach import DraftStatus
from app.services.outreach_service import (
    get_draft,
    list_drafts as _list_drafts,
    list_logs as _list_logs,
    review_draft,
    update_draft as _update_draft,
)


def list_drafts(
    db: Session, *, status: str | None = None, limit: int = 10
) -> dict:
    """List outreach drafts with optional status filter."""
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

    try:
        lid = uuid.UUID(lead_id)
    except ValueError:
        return {"error": "ID de lead inválido"}
    draft = generate_outreach_draft(db, lid)
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
    try:
        did = uuid.UUID(draft_id)
    except ValueError:
        return {"error": "ID de borrador inválido"}
    draft = review_draft(db, did, approved=True)
    if not draft:
        return {"error": "Borrador no encontrado"}
    return {"id": str(draft.id), "status": draft.status.value}


def reject_draft(
    db: Session, *, draft_id: str, reason: str | None = None
) -> dict:
    """Reject an outreach draft."""
    try:
        did = uuid.UUID(draft_id)
    except ValueError:
        return {"error": "ID de borrador inválido"}
    draft = review_draft(db, did, approved=False, feedback=reason)
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


# ---------------------------------------------------------------------------
# send_draft
# ---------------------------------------------------------------------------


def send_draft(db: Session, *, draft_id: str) -> dict:
    """Mark a draft as sent (actual email delivery is a v2 feature)."""
    try:
        did = uuid.UUID(draft_id)
    except ValueError:
        return {"error": "ID de borrador inválido"}

    draft = _update_draft(db, did, status=DraftStatus.SENT)
    if not draft:
        return {"error": "Borrador no encontrado"}

    # Fetch the lead's email for the response
    from app.services.lead_service import get_lead

    lead = get_lead(db, draft.lead_id)
    recipient_email = lead.email if lead else None

    return {
        "id": str(draft.id),
        "status": draft.status.value,
        "recipient_email": recipient_email,
    }


registry.register(ToolDefinition(
    name="send_draft",
    description=(
        "Enviar un borrador de outreach aprobado "
        "(requiere confirmación)"
    ),
    parameters=[
        ToolParameter("draft_id", "string", "UUID del borrador"),
    ],
    category="outreach",
    requires_confirmation=True,
    handler=send_draft,
))


# ---------------------------------------------------------------------------
# update_draft_content
# ---------------------------------------------------------------------------


def update_draft_content(
    db: Session,
    *,
    draft_id: str,
    subject: str | None = None,
    body: str | None = None,
) -> dict:
    """Update the subject and/or body of a draft."""
    try:
        did = uuid.UUID(draft_id)
    except ValueError:
        return {"error": "ID de borrador inválido"}

    draft = _update_draft(db, did, subject=subject, body=body)
    if not draft:
        return {"error": "Borrador no encontrado"}
    return {
        "id": str(draft.id),
        "subject": draft.subject,
        "body": draft.body,
        "status": draft.status.value,
    }


registry.register(ToolDefinition(
    name="update_draft_content",
    description="Editar el asunto y/o cuerpo de un borrador de outreach",
    parameters=[
        ToolParameter(
            "draft_id", "string", "UUID del borrador",
        ),
        ToolParameter(
            "subject", "string",
            "Nuevo asunto del email", required=False,
        ),
        ToolParameter(
            "body", "string",
            "Nuevo cuerpo del email", required=False,
        ),
    ],
    category="outreach",
    handler=update_draft_content,
))


# ---------------------------------------------------------------------------
# list_outreach_logs
# ---------------------------------------------------------------------------


def list_outreach_logs(
    db: Session,
    *,
    lead_id: str | None = None,
    limit: int = 20,
) -> dict:
    """List outreach activity logs."""
    parsed_lead_id = None
    if lead_id:
        try:
            parsed_lead_id = uuid.UUID(lead_id)
        except ValueError:
            return {"error": "ID de lead inválido (debe ser UUID)"}

    logs = _list_logs(
        db, lead_id=parsed_lead_id, limit=min(limit, 50),
    )
    return {
        "count": len(logs),
        "logs": [
            {
                "id": str(log.id),
                "lead_id": str(log.lead_id),
                "draft_id": str(log.draft_id) if log.draft_id else None,
                "action": log.action.value if log.action else None,
                "actor": log.actor,
                "detail": log.detail,
                "created_at": (
                    log.created_at.isoformat()
                    if log.created_at else None
                ),
            }
            for log in logs
        ],
    }


registry.register(ToolDefinition(
    name="list_outreach_logs",
    description=(
        "Listar el historial de actividad de outreach, "
        "opcionalmente filtrado por lead"
    ),
    parameters=[
        ToolParameter(
            "lead_id", "string",
            "UUID del lead para filtrar", required=False,
        ),
        ToolParameter(
            "limit", "integer",
            "Cantidad máxima de registros (default 20)",
            required=False,
        ),
    ],
    category="outreach",
    handler=list_outreach_logs,
))
