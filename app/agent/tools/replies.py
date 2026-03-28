"""Reply tools — generate and send reply assistant drafts."""

import uuid

from sqlalchemy.orm import Session

from app.agent.tool_registry import ToolDefinition, ToolParameter, registry


def generate_reply_draft(db: Session, *, message_id: str) -> dict:
    """Generate an LLM reply draft for an inbound message."""
    try:
        mid = uuid.UUID(message_id)
    except ValueError:
        return {"error": "ID de mensaje inválido (debe ser UUID)"}

    from app.services.reply_response_service import generate_reply_assistant_draft
    draft = generate_reply_assistant_draft(db, mid)
    if not draft:
        return {"error": "Mensaje no encontrado o sin contexto suficiente para generar respuesta"}
    return {
        "id": str(draft.id),
        "subject": draft.subject,
        "body": draft.body,
        "suggested_tone": draft.suggested_tone,
    }


def send_reply_draft(db: Session, *, message_id: str) -> dict:
    """Send the reply assistant draft for an inbound message."""
    try:
        mid = uuid.UUID(message_id)
    except ValueError:
        return {"error": "ID de mensaje inválido (debe ser UUID)"}

    try:
        from app.services.reply_send_service import send_reply_assistant_draft
        send_record = send_reply_assistant_draft(db, mid)
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "id": str(send_record.id),
        "status": send_record.status.value if send_record.status else None,
        "recipient_email": send_record.recipient_email,
    }


registry.register(ToolDefinition(
    name="generate_reply_draft",
    description=(
        "Generar un borrador de respuesta asistida por LLM para un mensaje entrante "
        "(requiere confirmación — invoca al modelo)"
    ),
    parameters=[
        ToolParameter("message_id", "string", "UUID del mensaje entrante"),
    ],
    category="replies",
    requires_confirmation=True,
    handler=generate_reply_draft,
))

registry.register(ToolDefinition(
    name="send_reply_draft",
    description=(
        "Enviar el borrador de respuesta asistida para un mensaje entrante "
        "(requiere confirmación — envía email real)"
    ),
    parameters=[
        ToolParameter("message_id", "string", "UUID del mensaje entrante"),
    ],
    category="replies",
    requires_confirmation=True,
    handler=send_reply_draft,
))
