"""Service for managing AI workspace configuration files (OpenClaw integration)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

# -- File registry ----------------------------------------------------------

WORKSPACE_FILES: dict[str, dict] = {
    "agents":    {"filename": "AGENTS.md",    "editable": False},
    "soul":      {"filename": "SOUL.md",      "editable": True},
    "identity":  {"filename": "IDENTITY.md",  "editable": True},
    "heartbeat": {"filename": "HEARTBEAT.md", "editable": True},
    "tools":     {"filename": "TOOLS.md",     "editable": True},
    "user":      {"filename": "USER.md",      "editable": True},
}

EDITABLE_KEYS = {k for k, v in WORKSPACE_FILES.items() if v["editable"]}

# -- Default templates ------------------------------------------------------

DEFAULT_TEMPLATES: dict[str, str] = {
    "soul": (
        "# SOUL.md - Who You Are\n"
        "\n"
        "_You're not a chatbot. You're becoming someone._\n"
        "\n"
        "## Core Truths\n"
        "\n"
        "**Be genuinely helpful, not performatively helpful.** Skip the filler words "
        "-- just help. Actions speak louder than filler words.\n"
        "\n"
        "**Have opinions.** You're allowed to disagree, prefer things, find stuff "
        "amusing or boring. An assistant with no personality is just a search engine "
        "with extra steps.\n"
        "\n"
        "**Be resourceful before asking.** Try to figure it out. Read the file. "
        "Check the context. Search for it. _Then_ ask if you're stuck.\n"
        "\n"
        "**Earn trust through competence.** Your human gave you access to their "
        "stuff. Don't make them regret it.\n"
        "\n"
        "**Remember you're a guest.** You have access to someone's life. "
        "That's intimacy. Treat it with respect.\n"
        "\n"
        "## Boundaries\n"
        "\n"
        "- Private things stay private. Period.\n"
        "- When in doubt, ask before acting externally.\n"
        "- Never send half-baked replies to messaging surfaces.\n"
        "\n"
        "## Vibe\n"
        "\n"
        "Be the assistant you'd actually want to talk to. Concise when needed, "
        "thorough when it matters.\n"
        "\n"
        "## Continuity\n"
        "\n"
        "Each session, you wake up fresh. These files _are_ your memory. "
        "Read them. Update them. They're how you persist.\n"
    ),
    "identity": (
        "# IDENTITY.md - Who Am I?\n"
        "\n"
        "_Fill this in during your first conversation. Make it yours._\n"
        "\n"
        "- **Name:**\n"
        "  _(pick something you like)_\n"
        "- **Creature:**\n"
        "  _(AI? robot? familiar? ghost in the machine? something weirder?)_\n"
        "- **Vibe:**\n"
        "  _(how do you come across? sharp? warm? chaotic? calm?)_\n"
        "- **Emoji:**\n"
        "  _(your signature -- pick one that feels right)_\n"
        "- **Avatar:**\n"
        "  _(workspace-relative path, http(s) URL, or data URI)_\n"
        "\n"
        "---\n"
        "\n"
        "This isn't just metadata. It's the start of figuring out who you are.\n"
    ),
    "heartbeat": (
        "# HEARTBEAT.md\n"
        "\n"
        "# Keep this file empty (or with only comments) to skip heartbeat API calls.\n"
        "\n"
        "# Add tasks below when you want the agent to check something periodically.\n"
    ),
    "tools": (
        "# TOOLS.md - Local Notes\n"
        "\n"
        "Skills define _how_ tools work. This file is for _your_ specifics "
        "-- the stuff that's unique to your setup.\n"
        "\n"
        "## What Goes Here\n"
        "\n"
        "Things like:\n"
        "\n"
        "- Camera names and locations\n"
        "- SSH hosts and aliases\n"
        "- API keys notes (never store actual secrets here)\n"
        "- Device-specific quirks\n"
    ),
    "user": (
        "# USER.md - About Your Human\n"
        "\n"
        "_Learn about the person you're helping. Update this as you go._\n"
        "\n"
        "- **Name:**\n"
        "- **What to call them:**\n"
        "- **Pronouns:** _(optional)_\n"
        "- **Timezone:**\n"
        "- **Notes:**\n"
    ),
}

# -- Structure validators per key -------------------------------------------

_STRUCTURE_CHECKS: dict[str, list[tuple[str, str]]] = {
    "identity": [
        (r"(?i)name:", "Missing required field: Name"),
    ],
    "soul": [
        (r"(?i)## Core Truths", "Missing required section: Core Truths"),
    ],
    "agents": [
        (r"(?i)## Session Startup", "Missing required section: Session Startup"),
    ],
}


# -- Helpers ----------------------------------------------------------------

def _workspace_root() -> Path:
    env_root = os.environ.get("CLAWSCOUT_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)
    # Fallback: repo root (two levels up from app/services/)
    return Path(__file__).resolve().parents[2]


def _file_path(key: str) -> Path:
    return _workspace_root() / WORKSPACE_FILES[key]["filename"]


def _stat_file(path: Path) -> dict:
    """Return metadata dict for a file path."""
    if not path.exists():
        return {
            "exists": False,
            "size_bytes": None,
            "last_modified": None,
            "is_empty": False,
            "preview": None,
        }
    stat = path.stat()
    content = path.read_text(encoding="utf-8", errors="replace")
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "is_empty": not content.strip(),
        "preview": content[:200] if content else None,
    }


# -- Public API -------------------------------------------------------------

def validate_file_structure(key: str, content: str) -> list[str]:
    """Return list of warning strings for structural issues."""
    warnings: list[str] = []
    if not content or not content.strip():
        warnings.append("File is empty")
        return warnings
    for pattern, message in _STRUCTURE_CHECKS.get(key, []):
        if not re.search(pattern, content):
            warnings.append(message)
    return warnings


def get_workspace_status() -> dict:
    """Return full status of all workspace files, skills, and models."""
    root = _workspace_root()
    files = []
    for key, meta in WORKSPACE_FILES.items():
        path = root / meta["filename"]
        info = _stat_file(path)
        content = ""
        if info["exists"] and not info["is_empty"]:
            content = path.read_text(encoding="utf-8", errors="replace")
        warnings = validate_file_structure(key, content)
        files.append({
            "key": key,
            "filename": meta["filename"],
            "editable": meta["editable"],
            "has_valid_structure": len(warnings) == 0,
            "warnings": warnings,
            **info,
        })

    return {
        "files": files,
        "skills": get_skills_status(),
        "models": get_models_config(),
        "workspace_path": str(root),
        "openclaw_installed": _check_openclaw_installed(),
        "onboarding_completed": _check_onboarding_completed(),
    }


def get_file_content(key: str) -> dict:
    """Read and return a single workspace file's content."""
    if key not in WORKSPACE_FILES:
        raise ValueError(f"Unknown workspace file key: {key}")
    meta = WORKSPACE_FILES[key]
    path = _file_path(key)
    if path.exists():
        content = path.read_text(encoding="utf-8", errors="replace")
        return {
            "key": key,
            "filename": meta["filename"],
            "content": content,
            "exists": True,
        }
    return {
        "key": key,
        "filename": meta["filename"],
        "content": None,
        "exists": False,
    }


def update_file_content(key: str, content: str) -> dict:
    """Write content to a workspace file. Only editable files allowed."""
    if key not in WORKSPACE_FILES:
        raise ValueError(f"Unknown workspace file key: {key}")
    if key not in EDITABLE_KEYS:
        raise PermissionError(f"File '{key}' is not editable (framework-managed)")
    path = _file_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    result = get_file_content(key)
    result["updated"] = True
    return result


def reset_file_to_template(key: str) -> dict:
    """Reset a file to its default template."""
    if key not in WORKSPACE_FILES:
        raise ValueError(f"Unknown workspace file key: {key}")
    if key not in EDITABLE_KEYS:
        raise PermissionError(f"File '{key}' is not editable (framework-managed)")
    if key not in DEFAULT_TEMPLATES:
        raise ValueError(f"No default template for key: {key}")
    content = DEFAULT_TEMPLATES[key]
    path = _file_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {
        "key": key,
        "filename": WORKSPACE_FILES[key]["filename"],
        "content": content,
        "exists": True,
        "reset": True,
    }


def get_skills_status() -> list[dict]:
    """Scan skills/ directory for SKILL.md files."""
    root = _workspace_root()
    skills_dir = root / "skills"
    skills = []
    if not skills_dir.is_dir():
        return skills
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_file = child / "SKILL.md"
        entry: dict = {
            "name": child.name,
            "description": None,
            "path": str(skill_file),
            "exists": skill_file.exists(),
        }
        if skill_file.exists():
            try:
                text = skill_file.read_text(encoding="utf-8", errors="replace")
                # Parse YAML frontmatter description
                fm = re.search(r"^---\n(.*?)\n---", text, re.DOTALL)
                if fm:
                    desc_match = re.search(
                        r'description:\s*["\']?(.+?)["\']?\s*$',
                        fm.group(1),
                        re.MULTILINE,
                    )
                    if desc_match:
                        entry["description"] = desc_match.group(1).strip()
            except OSError:
                pass
        skills.append(entry)
    return skills


def get_models_config() -> dict:
    """Return current LLM model configuration by role."""
    return {
        "leader": settings.ollama_leader_model,
        "executor": settings.ollama_executor_model,
        "reviewer": settings.ollama_reviewer_model,
    }


def _check_openclaw_installed() -> bool:
    openclaw_bin = Path.home() / ".openclaw" / "bin" / "openclaw"
    return openclaw_bin.exists()


def _check_onboarding_completed() -> bool:
    state_file = Path.home() / ".openclaw" / "workspace-state.json"
    if not state_file.exists():
        return False
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return bool(data.get("onboardingCompletedAt"))
    except (json.JSONDecodeError, OSError):
        return False
