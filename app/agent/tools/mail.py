"""Mail tools — inbound sync, listing, and classification."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry
from app.services.inbound_mail_service import (
    InboundMailServiceError,
    list_inbound_messages as _list_inbound_messages,
    sync_inbound_messages as _sync_inbound_messages,
)
from app.services.reply_classification_service import (
    classify_inbound_message as _classify_inbound_message,
)


def sync_inbound_mail(db: Session, *, limit: int = 25) -> dict:
    """Trigger inbound mail sync via IMAP."""
    try:
        sync_run = _sync_inbound_messages(db, limit=limit)
    except InboundMailServiceError as exc:
        return {"error": str(exc)}
    failed = max(0, sync_run.fetched_count - sync_run.new_count - sync_run.deduplicated_count)
    return {
        "status": sync_run.status,
        "messages_synced": sync_run.new_count,
        "messages_failed": failed,
    }


def list_inbound(
    db: Session,
    *,
    lead_id: str | None = None,
    classification_status: str | None = None,
    limit: int = 20,
) -> dict:
    """List inbound messages with optional filters."""
    parsed_lead_id: uuid.UUID | None = None
    if lead_id:
        try:
            parsed_lead_id = uuid.UUID(lead_id)
        except ValueError:
            return {"error": "ID de lead inválido (debe ser UUID)"}

    messages = _list_inbound_messages(
        db,
        lead_id=parsed_lead_id,
        classification_status=classification_status,
        limit=min(limit, 50),
    )
    return {
        "count": len(messages),
        "messages": [
            {
                "id": str(m.id),
                "from_email": m.from_email,
                "subject": m.subject,
                "classification_label": m.classification_label,
                "received_at": m.received_at.isoformat() if m.received_at else None,
            }
            for m in messages
        ],
    }


def classify_inbound_message(db: Session, *, message_id: str) -> dict:
    """Classify a single inbound message using the LLM executor."""
    try:
        mid = uuid.UUID(message_id)
    except ValueError:
        return {"error": "ID de mensaje inválido (debe ser UUID)"}

    message = _classify_inbound_message(db, mid)
    if not message:
        return {"error": "Mensaje no encontrado"}
    return {
        "id": str(message.id),
        "classification_label": message.classification_label,
        "confidence": message.confidence,
        "summary": message.summary,
    }


registry.register(ToolDefinition(
    name="sync_inbound_mail",
    description=(
        "Sincronizar correos entrantes desde el servidor IMAP "
        "(requiere confirmación — dispara la conexión al servidor de mail)"
    ),
    parameters=[
        ToolParameter(
            "limit", "integer",
            "Cantidad máxima de mensajes a buscar (default 25)",
            required=False,
        ),
    ],
    category="mail",
    requires_confirmation=True,
    handler=sync_inbound_mail,
))

registry.register(ToolDefinition(
    name="list_inbound_messages",
    description="Listar mensajes entrantes con filtros opcionales de lead y estado de clasificación",
    parameters=[
        ToolParameter("lead_id", "string", "UUID del lead asociado", required=False),
        ToolParameter(
            "classification_status", "string",
            "Estado de clasificación",
            required=False,
            enum=["pending", "classified", "failed"],
        ),
        ToolParameter(
            "limit", "integer",
            "Cantidad máxima de resultados (default 20)",
            required=False,
        ),
    ],
    category="mail",
    handler=list_inbound,
))

registry.register(ToolDefinition(
    name="classify_inbound_message",
    description="Clasificar un mensaje entrante individual usando el modelo LLM executor",
    parameters=[
        ToolParameter("message_id", "string", "UUID del mensaje entrante"),
    ],
    category="mail",
    handler=classify_inbound_message,
))
