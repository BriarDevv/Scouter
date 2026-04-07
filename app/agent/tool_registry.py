"""Central tool registry for the Scouter agent.

Provides ``ToolDefinition`` metadata, parameter validation, and Hermes 3
compatible ``<tools>`` schema generation.  A module-level ``registry``
singleton is exposed for convenience.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

_PYTHON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


@dataclass(frozen=True, slots=True)
class ToolParameter:
    """Description of a single tool parameter."""

    name: str
    type: str  # "string" | "integer" | "number" | "boolean" | "array" | "object"
    description: str
    required: bool = True
    enum: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Full definition of a tool the agent can invoke."""

    name: str
    description: str  # Spanish (es-AR), shown to the LLM
    parameters: list[ToolParameter] = field(default_factory=list)
    category: str = "general"
    requires_confirmation: bool = False
    handler: Callable[..., Any] | None = None
    takes_db: bool = False


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Thread-safe registry of ``ToolDefinition`` objects.

    Use :pydata:`registry` (the module-level singleton) instead of
    instantiating this class directly.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    # -- mutators -----------------------------------------------------------

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition.

        Overwrites any previous registration with the same name and logs a
        warning if that happens.  Inspects the handler signature once at
        registration time to set ``takes_db``.
        """
        if tool.name in self._tools:
            logger.warning("tool_overwritten", tool_name=tool.name)

        # Cache whether the handler expects ``db`` as its first parameter so
        # _execute_tool does not need to call inspect.signature on every call.
        if tool.handler is not None and not tool.takes_db:
            try:
                params = list(inspect.signature(tool.handler).parameters.keys())
                if params and params[0] == "db":
                    # ToolDefinition is frozen; rebuild with takes_db=True
                    tool = ToolDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.parameters,
                        category=tool.category,
                        requires_confirmation=tool.requires_confirmation,
                        handler=tool.handler,
                        takes_db=True,
                    )
            except (TypeError, ValueError):
                pass

        self._tools[tool.name] = tool
        logger.debug("tool_registered", tool_name=tool.name, category=tool.category)

    # -- accessors ----------------------------------------------------------

    def get(self, name: str) -> ToolDefinition | None:
        """Return the ``ToolDefinition`` for *name*, or ``None``."""
        return self._tools.get(name)

    def list_all(self) -> list[ToolDefinition]:
        """Return every registered tool in insertion order."""
        return list(self._tools.values())

    # -- schema generation --------------------------------------------------

    def _parameter_schema(self, param: ToolParameter) -> dict[str, Any]:
        """Build the JSON Schema fragment for a single parameter."""
        schema: dict[str, Any] = {
            "type": param.type,
            "description": param.description,
        }
        if param.enum is not None:
            schema["enum"] = param.enum
        return schema

    def _tool_json(self, tool: ToolDefinition) -> dict[str, Any]:
        """Build the JSON-serialisable dict for one tool."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for param in tool.parameters:
            properties[param.name] = self._parameter_schema(param)
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_hermes_schema(self) -> str:
        """Generate the ``<tools>`` XML block with JSON tool schemas.

        The output is compatible with Hermes 3 function-calling conventions::

            <tools>
            <tool>
            {"type": "function", "function": { ... }}
            </tool>
            ...
            </tools>
        """
        if not self._tools:
            return "<tools>\n</tools>"

        lines: list[str] = ["<tools>"]
        # Group tools by category for better model navigation
        by_category: dict[str, list[ToolDefinition]] = {}
        for tool in self._tools.values():
            cat = tool.category or "general"
            by_category.setdefault(cat, []).append(tool)
        for cat, tools in by_category.items():
            lines.append(f"<!-- {cat} tools ({len(tools)}) -->")
            for tool in tools:
                lines.append("<tool>")
                lines.append(json.dumps(self._tool_json(tool), ensure_ascii=False))
                lines.append("</tool>")
        lines.append("</tools>")
        return "\n".join(lines)

    # -- validation ---------------------------------------------------------

    def validate_call(
        self,
        name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and coerce *args* against the parameter definitions.

        Returns a *new* dict with coerced values.

        Raises:
            KeyError: If *name* is not a registered tool.
            ValueError: If a required parameter is missing or type coercion
                fails.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")

        param_map = {p.name: p for p in tool.parameters}
        validated: dict[str, Any] = {}

        # Check required params are present
        for param in tool.parameters:
            if param.required and param.name not in args:
                raise ValueError(
                    f"Herramienta '{name}': parámetro obligatorio '{param.name}' no proporcionado"
                )

        # Coerce and validate provided args
        for key, value in args.items():
            param = param_map.get(key)
            if param is None:
                # Unknown parameter — pass through without coercion
                validated[key] = value
                continue

            # Enum check
            if param.enum is not None and str(value) not in param.enum:
                raise ValueError(
                    f"Herramienta '{name}': parámetro '{key}' debe ser "
                    f"uno de {param.enum}, recibido '{value}'"
                )

            # Type coercion for scalars
            target_type = _PYTHON_TYPE_MAP.get(param.type)
            if target_type is not None and not isinstance(value, target_type):
                try:
                    value = target_type(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Herramienta '{name}': no se pudo convertir '{key}' a {param.type}: {exc}"
                    ) from exc

            validated[key] = value

        return validated


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

registry = ToolRegistry()
