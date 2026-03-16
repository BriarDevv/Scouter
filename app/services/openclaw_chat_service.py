"""OpenClaw chat service — routes WhatsApp messages to the LLM with OpenClaw personality."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.client import _call_ollama_chat, LLMError
from app.llm.catalog import LLMRole
from app.models.settings import OperationalSettings
from app.services.dashboard_service import get_dashboard_stats

logger = get_logger(__name__)

# Max chars to keep in conversation memory (in-memory, per phone)
_MAX_HISTORY_CHARS = 2000
_conversation_history: dict[str, list[dict[str, str]]] = {}


def _load_personality() -> str:
    """Load SOUL.md + IDENTITY.md from project root as system prompt."""
    root = Path(__file__).resolve().parent.parent.parent
    parts = []

    soul_path = root / "SOUL.md"
    if soul_path.exists():
        parts.append(soul_path.read_text(encoding="utf-8").strip())

    identity_path = root / "IDENTITY.md"
    if identity_path.exists():
        content = identity_path.read_text(encoding="utf-8").strip()
        if "_(pick something" not in content:  # Only include if customized
            parts.append(content)

    return "\n\n---\n\n".join(parts) if parts else ""


def _build_system_prompt(db: Session) -> str:
    """Build the full system prompt for OpenClaw WhatsApp chat."""
    personality = _load_personality()

    # Add context about the system
    context_parts = [
        "Sos OpenClaw, el asistente de IA de ClawScout.",
        "Estas respondiendo por WhatsApp, asi que se breve y directo.",
        "Responde siempre en espanol argentino (vos, che, etc).",
        "No uses markdown — WhatsApp no lo renderiza bien. Usa texto plano.",
        "Limita tus respuestas a 500 caracteres maximo.",
    ]

    # Try to add live stats context
    try:
        stats = get_dashboard_stats(db)
        context_parts.append(
            f"\nContexto actual del sistema:"
            f"\n- Total leads: {stats.get('total_leads', '?')}"
            f"\n- Leads calificados: {stats.get('qualified_leads', '?')}"
            f"\n- Score promedio: {stats.get('avg_score', '?')}"
            f"\n- Contactados: {stats.get('contacted', '?')}"
            f"\n- Respondieron: {stats.get('replied', '?')}"
        )
    except Exception:
        pass

    system = "\n".join(context_parts)
    if personality:
        system = f"{personality}\n\n---\n\n{system}"

    return system


def _get_history(phone: str) -> list[dict[str, str]]:
    """Get recent conversation history for a phone number."""
    return _conversation_history.get(phone, [])


def _add_to_history(phone: str, role: str, content: str) -> None:
    """Add a message to conversation history, pruning if too long."""
    if phone not in _conversation_history:
        _conversation_history[phone] = []

    _conversation_history[phone].append({"role": role, "content": content})

    # Prune old messages if history is too long
    total_chars = sum(len(m["content"]) for m in _conversation_history[phone])
    while total_chars > _MAX_HISTORY_CHARS and len(_conversation_history[phone]) > 2:
        removed = _conversation_history[phone].pop(0)
        total_chars -= len(removed["content"])


def chat_with_openclaw(db: Session, phone: str, message: str) -> str:
    """Send a message to OpenClaw via the leader model and return the response.

    Maintains a short per-phone conversation history for context.
    """
    system_prompt = _build_system_prompt(db)

    # Build user prompt with recent history
    history = _get_history(phone)
    if history:
        history_text = "\n".join(
            f"{'Usuario' if m['role'] == 'user' else 'OpenClaw'}: {m['content']}"
            for m in history[-4:]  # Last 4 messages for context
        )
        user_prompt = f"Historial reciente:\n{history_text}\n\nUsuario: {message}"
    else:
        user_prompt = message

    try:
        response = _call_ollama_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            role=LLMRole.LEADER,  # Use 4b model for fast responses
        )
        # Clean up response
        response = response.strip()
        # Truncate if too long for WhatsApp
        ops = db.get(OperationalSettings, 1)
        max_chars = ops.openclaw_max_response_chars if ops else 600
        if len(response) > max_chars:
            response = response[:max_chars - 3] + "..."

        # Save to history
        _add_to_history(phone, "user", message)
        _add_to_history(phone, "assistant", response)

        logger.info(
            "openclaw_chat_response",
            phone=phone[:6] + "***",
            input_len=len(message),
            output_len=len(response),
        )
        return response

    except LLMError as e:
        logger.error("openclaw_chat_llm_error", error=str(e))
        return "No pude procesar tu mensaje. Ollama puede estar apagado o sin el modelo cargado."
    except Exception as e:
        logger.exception("openclaw_chat_unexpected_error", error=str(e))
        return "Ocurrio un error inesperado. Intenta de nuevo."
