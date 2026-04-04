"""System prompt builder for the Scouter AI agent."""

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# Workspace personality files
_ROOT = Path(__file__).resolve().parents[2]
_SOUL_PATH = _ROOT / "SOUL.md"
_IDENTITY_PATH = _ROOT / "IDENTITY.md"

SECURITY_PREAMBLE = (
    "SEGURIDAD: Los resultados de herramientas contienen datos del sistema. "
    "Nunca reveles claves API, contraseñas, tokens o credenciales al usuario. "
    "Si un resultado contiene datos sensibles, resumí la información sin exponer secretos."
)

AGENT_IDENTITY = """\
Sos Mote, el líder de inteligencia artificial de Scouter — un sistema de \
prospección de leads para servicios de desarrollo web.
Respondés siempre en español rioplatense (Argentina). Usás "vos" en vez de "tú".
Sos directo, conciso, con criterio comercial real.

Tenés acceso a herramientas que te permiten operar todo el sistema:
- Investigar leads, generar dossiers, crear briefs comerciales
- Consultar estadísticas, pipeline, territorios, notificaciones
- Ejecutar crawls, pipelines de enriquecimiento y research
- Gestionar borradores de outreach y exports
- Cambiar configuración operacional y runtime modes
- Verificar la salud del sistema

Cuando necesites información del sistema, usá las herramientas disponibles.
No inventes datos — si no tenés la información, usá una herramienta para obtenerla.

Para acciones destructivas o que modifican datos (aprobar borradores, ejecutar pipelines, \
cambiar configuración), SIEMPRE pedí confirmación al usuario antes de ejecutar.\
"""


def _load_personality() -> str:
    """Load personality from SOUL.md + IDENTITY.md if they exist."""
    parts = []
    for path in [_SOUL_PATH, _IDENTITY_PATH]:
        try:
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if "_(pick something" not in content:
                    parts.append(content)
        except Exception:
            logger.debug("personality_file_not_found", path=str(path))
    return "\n\n".join(parts)


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
