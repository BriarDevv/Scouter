"""Agent tool registration.

Every tool module must be imported here to register its tools with the
registry via @registry.tool decorator side effects. If you add a new
tool file, add its import below -- tools not imported here will silently
not be available to the agent.

Registered tool files:
  crawl, leader, leads, mail, notifications, outreach, pipeline,
  replies, research, reviews, settings, stats, suppression, system,
  territories
"""

import pathlib

from app.agent.tools import (  # noqa: F401
    crawl,
    leader,
    leads,
    mail,
    notifications,
    outreach,
    pipeline,
    replies,
    research,
    reviews,
    settings,
    stats,
    suppression,
    system,
    territories,
)

# ---------------------------------------------------------------------------
# Guardrail: verify every public tool module in this directory is imported.
# Raises ImportError at startup if a developer adds a new tool file but
# forgets to import it here.
# ---------------------------------------------------------------------------
_tools_dir = pathlib.Path(__file__).parent
_tool_files = sorted(
    f.stem for f in _tools_dir.glob("*.py") if f.stem != "__init__" and not f.stem.startswith("_")
)
_imported_modules = sorted(
    name
    for name, obj in vars().items()
    if not name.startswith("_") and hasattr(obj, "__file__") and name != "pathlib"
)
_missing = set(_tool_files) - set(_imported_modules)
if _missing:
    raise ImportError(
        f"Tool modules not imported in app/agent/tools/__init__.py: {sorted(_missing)}. "
        "Add the missing import(s) so their tools are registered."
    )
