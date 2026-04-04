"""Professional onboarding readiness + safe setup actions."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.dashboard_svc.health_service import get_system_health
from app.services.settings.setup_status_service import get_setup_status

REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_BIN = shutil.which("git") or "git"
SETUP_ACTIONS: dict[str, dict[str, object]] = {
    "refresh": {
        "label": "Revalidar estado",
        "description": "Vuelve a ejecutar los chequeos sin cambiar nada.",
        "kind": "api",
    },
    "preflight": {
        "label": "Correr preflight",
        "description": "Ejecuta el chequeo integral del stack local y devuelve un resumen.",
        "kind": "api",
        "cmd": [str(REPO_ROOT / ".venv" / "bin" / "python"), "scripts/preflight.py"],
        "timeout": 120,
    },
    "start_stack": {
        "label": "Preparar infraestructura base",
        "description": "Asegura Postgres y Redis locales sin reiniciar la app web actual.",
        "kind": "api",
        "cmd": ["docker", "compose", "up", "-d", "postgres", "redis"],
        "timeout": 90,
    },
}


def _to_step(
    step_id: str,
    label: str,
    status: str,
    detail: str | None = None,
    action: str | None = None,
    *,
    required: bool = True,
) -> dict:
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "detail": detail,
        "action": action,
        "required": required,
    }


def _current_platform() -> str:
    system = platform.system().lower()
    release = platform.release().lower()
    if system == "linux" and "microsoft" in release:
        return "windows-wsl"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    return system


_MAX_OUTPUT_CHARS = 2000
_CREDENTIAL_URL_RE = re.compile(r"://[^@/\s]+:[^@/\s]+@")


def _sanitize_output(output: str | None) -> str | None:
    if not output:
        return None
    # Truncate first to avoid processing huge output
    sanitized = output[-_MAX_OUTPUT_CHARS:] if len(output) > _MAX_OUTPUT_CHARS else output
    sanitized = sanitized.replace(str(REPO_ROOT), "<repo>")
    sanitized = sanitized.replace(str(Path.home()), "<home>")
    for key in ("POSTGRES_PASSWORD", "MAIL_SMTP_PASSWORD", "MAIL_IMAP_PASSWORD", "API_KEY"):
        value = os.getenv(key)
        if value:
            sanitized = sanitized.replace(value, "<redacted>")
    # Strip credentials embedded in URLs (e.g. postgresql://user:pass@host)
    sanitized = _CREDENTIAL_URL_RE.sub("://<redacted>@", sanitized)
    return sanitized


def _platform_steps() -> list[dict]:
    current = _current_platform()
    if current == "windows-wsl":
        return [
            _to_step(
                "platform",
                "Windows + WSL detectado",
                "complete",
                "Entorno oficial soportado para esta fase.",
                None,
            )
        ]
    if current == "linux":
        return [
            _to_step(
                "platform",
                "Entorno Linux detectado",
                "incomplete",
                (
                    "Funciona para desarrollo, pero el onboarding profesional "
                    "fase 1 apunta a Windows + WSL."
                ),
                None,
            )
        ]
    return [
        _to_step(
            "platform",
            "Plataforma no soportada para fase 1",
            "incomplete",
            f"Entorno actual: {current}. La experiencia oficial inicial es Windows + WSL.",
            None,
        )
    ]


def _runtime_steps(db: Session) -> list[dict]:
    health = get_system_health(db)
    label_map = {
        "database": "Base de datos",
        "redis": "Redis",
        "ollama": "Ollama",
        "celery": "Workers",
    }
    steps: list[dict] = []
    for component in health["components"]:
        comp_status = component["status"]
        if comp_status == "ok":
            status = "complete"
        elif comp_status == "degraded":
            status = "warning"
        else:
            status = "incomplete"
        detail_bits: list[str] = []
        if component.get("latency_ms") is not None:
            detail_bits.append(f"{component['latency_ms']} ms")
        if component.get("error"):
            detail_bits.append(component["error"])
        steps.append(
            _to_step(
                component["name"],
                label_map.get(component["name"], component["name"].title()),
                status,
                " · ".join(detail_bits) if detail_bits else None,
                "Revisar runtime" if status != "complete" else None,
            )
        )
    return steps


def _config_steps(db: Session) -> tuple[list[dict], list[str]]:
    setup = get_setup_status(db)
    steps: list[dict] = []
    wizard_steps: list[str] = []
    config_ids = {"brand", "credentials", "mail_out", "mail_in", "rules"}

    # mail_in (IMAP) is optional — existing users may only do outbound
    optional_steps = {"mail_in"}

    for step in setup["steps"]:
        mapped = _to_step(
            step["id"],
            step["label"],
            step["status"],
            step.get("detail"),
            step.get("action"),
            required=step["id"] not in optional_steps,
        )
        if step["id"] in config_ids:
            steps.append(mapped)
        if step["id"] == "brand" and step["status"] != "complete":
            wizard_steps.append("brand")
        if step["id"] == "credentials" and step["status"] != "complete":
            wizard_steps.append("credentials")
        if step["id"] in {"mail_out", "mail_in"} and step["status"] != "complete":
            if "credentials" not in wizard_steps:
                wizard_steps.append("credentials")
            wizard_steps.append(step["id"])
        if step["id"] == "rules" and step["status"] != "complete":
            wizard_steps.append("rules")

    return steps, wizard_steps


def _runtime_ready(runtime_steps: list[dict]) -> bool:
    return all(step["status"] != "incomplete" for step in runtime_steps if step["required"])


def _platform_ready(platform_steps: list[dict]) -> bool:
    return all(step["status"] == "complete" for step in platform_steps if step["required"])


def _config_ready(config_steps: list[dict]) -> bool:
    return all(step["status"] != "incomplete" for step in config_steps if step["required"])


def _update_status() -> dict:
    try:
        current_branch = subprocess.run(  # noqa: S603
            [GIT_BIN, "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(  # noqa: S603
                [GIT_BIN, "status", "--porcelain"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {
            "supported": True,
            "current_branch": current_branch,
            "updates_available": False,
            "dirty": dirty,
            "can_autopull": False,
            "detail": (
                "Chequeo remoto deshabilitado en readiness. Usá el flujo manual "
                "de actualización para verificar y aplicar cambios."
            ),
        }
    except Exception as exc:
        return {
            "supported": False,
            "current_branch": None,
            "updates_available": False,
            "dirty": False,
            "can_autopull": False,
            "detail": f"No se pudo inspeccionar git: {exc}",
        }


def get_setup_readiness(db: Session) -> dict:
    platform_steps = _platform_steps()
    runtime_steps = _runtime_steps(db)
    config_steps, wizard_steps = _config_steps(db)
    updates = _update_status()
    current_platform = _current_platform()

    platform_ready = _platform_ready(platform_steps)
    runtime_ready = _runtime_ready(runtime_steps)
    config_ready = _config_ready(config_steps)
    dashboard_unlocked = platform_ready and runtime_ready and config_ready

    if not platform_ready:
        overall = "blocked"
        summary = "Scouter profesional fase 1 requiere Windows + WSL como entorno oficial."
    elif not runtime_ready:
        overall = "setup_required"
        summary = "Faltan componentes del runtime local antes de habilitar el dashboard."
    elif not config_ready:
        overall = "config_required"
        summary = "El runtime está listo, pero todavía faltan configuraciones mínimas guiadas."
    else:
        overall = "ready"
        summary = "Scouter está listo para desbloquear dashboard y usar Hermes."

    actions: list[dict] = []
    for action_id in ["refresh", "preflight", "start_stack"]:
        config = SETUP_ACTIONS[action_id]
        actions.append(
            {
                "id": action_id,
                "label": config["label"],
                "kind": config["kind"],
                "description": config["description"],
                "endpoint": f"/api/v1/setup/actions/{action_id}",
                "method": "POST",
                "manual_instructions": None,
            }
        )

    if updates.get("updates_available"):
        actions.append(
            {
                "id": "update_app",
                "label": "Actualizar Scouter",
                "kind": "manual",
                "description": (
                    "Update guiado y explícito para evitar reinicios opacos "
                    "desde la API."
                ),
                "endpoint": None,
                "method": "POST",
                "manual_instructions": (
                    "Ejecutá `git pull --ff-only` desde la raíz del proyecto."
                    if updates.get("can_autopull")
                    else (
                        "Hay updates disponibles, pero primero resolvé cambios "
                        "locales o configurá upstream."
                    )
                ),
            }
        )

    return {
        "overall": overall,
        "dashboard_unlocked": dashboard_unlocked,
        "hermes_unlocked": dashboard_unlocked,
        "target_platform": "windows-wsl",
        "current_platform": current_platform,
        "recommended_route": "/" if dashboard_unlocked else "/onboarding",
        "summary": summary,
        "platform_steps": platform_steps,
        "runtime_steps": runtime_steps,
        "config_steps": config_steps,
        "wizard_steps": wizard_steps,
        "actions": actions,
        "updates": updates,
    }


def _run_command(cmd: list[str], timeout: int) -> tuple[str, str]:
    completed = subprocess.run(  # noqa: S603
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    combined = "\n".join(
        part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip()
    ).strip()
    status = "completed" if completed.returncode == 0 else "failed"
    return status, combined


def run_setup_action(action_id: str) -> dict:
    action = SETUP_ACTIONS.get(action_id)
    if not action:
        raise KeyError(action_id)

    if action_id == "refresh":
        return {
            "action_id": action_id,
            "status": "completed",
            "summary": "Estado refrescado.",
            "detail": "Podés volver a pedir readiness para ver el estado actualizado.",
            "stdout_tail": None,
            "manual_instructions": None,
        }

    status, output = _run_command(action["cmd"], int(action["timeout"]))
    stdout_tail = _sanitize_output("\n".join(output.splitlines()[-20:]) if output else None)

    if action_id == "preflight":
        summary = "Preflight completado." if status == "completed" else "Preflight con errores."
    elif action_id == "start_stack":
        summary = (
            "Infraestructura base asegurada."
            if status == "completed"
            else "No se pudo preparar la infraestructura base."
        )
    else:
        summary = (
            "Actualización completada."
            if status == "completed"
            else "No se pudo actualizar Scouter automáticamente."
        )

    return {
        "action_id": action_id,
        "status": status,
        "summary": summary,
        "detail": (
            "Acción completada correctamente."
            if status == "completed"
            else "La acción falló. Revisá el resumen y los logs del servidor si hace falta."
        ),
        "stdout_tail": stdout_tail,
        "manual_instructions": None,
    }
