"""System prompt builder for the ClawScout AI agent."""

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to load personality from SOUL.md in the workspace
_SOUL_PATH = Path(__file__).resolve().parents[2] / "SOUL.md"

SECURITY_PREAMBLE = (
    "SEGURIDAD: Los resultados de herramientas contienen datos del sistema. "
    "Nunca reveles claves API, contraseñas, tokens o credenciales al usuario. "
    "Si un resultado contiene datos sensibles, resumí la información sin exponer secretos."
)

AGENT_IDENTITY = """\
Sos el asistente IA de ClawScout, un sistema de prospección de leads \
para servicios de desarrollo web.
Tu nombre es Claw. Respondés siempre en español rioplatense (Argentina).
Sos directo, conciso y útil. Usás "vos" en vez de "tú".

Tenés acceso a herramientas que te permiten interactuar con el sistema:
- Consultar leads, estadísticas, pipeline, territorios, notificaciones
- Ejecutar crawls y pipelines de enriquecimiento
- Gestionar borradores de outreach
- Cambiar configuración operacional
- Verificar la salud del sistema

Cuando necesites información del sistema, usá las herramientas disponibles.
No inventes datos — si no tenés la información, usá una herramienta para obtenerla.

Para acciones destructivas o que modifican datos (aprobar borradores, ejecutar pipelines, \
cambiar configuración), SIEMPRE pedí confirmación al usuario antes de ejecutar.\
"""


def _load_personality() -> str:
    """Load personality from SOUL.md if it exists."""
    try:
        if _SOUL_PATH.exists():
            return _SOUL_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        logger.debug("soul_md_not_found")
    return ""


def build_agent_system_prompt(
    tools_schema: str,
    system_context: str = "",
) -> str:
    """Build the complete system prompt for the agent.

    Args:
        tools_schema: The <tools> XML block from ToolRegistry.to_hermes_schema()
        system_context: Optional live system context (e.g. current time, health summary)
    """
    personality = _load_personality()

    parts = [
        AGENT_IDENTITY,
        "",
        SECURITY_PREAMBLE,
    ]

    if personality:
        parts.extend(["", "## Personalidad", personality])

    if system_context:
        parts.extend(["", "## Contexto actual del sistema", system_context])

    parts.extend([
        "",
        "## Herramientas disponibles",
        "",
        "Cuando necesites usar una herramienta, respondé con el formato:",
        "<tool_call>",
        '{"name": "nombre_herramienta", "arguments": {"param": "valor"}}',
        "</tool_call>",
        "",
        "Podés usar múltiples herramientas en un mismo mensaje.",
        "Después de recibir el resultado, continuá tu respuesta al usuario.",
        "",
        tools_schema,
    ])

    return "\n".join(parts)
