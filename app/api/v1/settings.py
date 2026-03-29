from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_session
from app.core.config import settings as env
from app.schemas.mail_credentials import (
    ConnectionTestResult,
    MailCredentialsResponse,
    MailCredentialsUpdate,
    SetupStatusResponse,
)
from app.schemas.operational_settings import (
    CredentialStatusItem,
    CredentialsStatusResponse,
    OperationalSettingsResponse,
    OperationalSettingsUpdate,
)
from app.schemas.settings import LLMSettingsResponse, MailSettingsResponse
from app.services.mail_credentials_service import (
    get_or_create as get_creds,
    test_imap,
    test_smtp,
    to_response_dict as creds_to_dict,
    update_credentials,
)
from app.services.operational_settings_service import (
    get_or_create,
    to_response_dict,
    update_operational_settings,
)
from app.services.settings_service import get_llm_settings, get_mail_settings
from app.services.setup_status_service import get_setup_status

router = APIRouter(prefix="/settings", tags=["settings"])


# ── Read-only env-based settings ──────────────────────────────────────

@router.get("/llm", response_model=LLMSettingsResponse)
def llm_settings():
    """Return the active LLM configuration (read-only from env)."""
    return get_llm_settings()


@router.get("/mail", response_model=MailSettingsResponse)
def mail_settings(db=Depends(get_session)):
    """Return effective mail settings (DB overrides + env fallback)."""
    return get_mail_settings(db)


# ── Operational settings (brand, overrides, rules) ────────────────────

@router.get("/operational", response_model=OperationalSettingsResponse)
def get_operational(db=Depends(get_session)):
    """Return the current operational settings."""
    row = get_or_create(db)
    return to_response_dict(row)


@router.patch("/operational", response_model=OperationalSettingsResponse)
def patch_operational(body: OperationalSettingsUpdate, db=Depends(get_session)):
    """Partial-update operational settings. Only sent fields are modified."""
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update provided.")
    row = update_operational_settings(db, updates)
    return to_response_dict(row)


# ── Mail credentials (DB-stored, passwords write-only) ────────────────

@router.get("/mail-credentials", response_model=MailCredentialsResponse)
def get_mail_credentials(db=Depends(get_session)):
    """Return mail connection settings. Passwords never exposed — only presence flags."""
    row = get_creds(db)
    return creds_to_dict(row)


@router.patch("/mail-credentials", response_model=MailCredentialsResponse)
def patch_mail_credentials(body: MailCredentialsUpdate, db=Depends(get_session)):
    """Update mail connection settings. Include password only when changing it."""
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update provided.")
    row = update_credentials(db, updates)
    return creds_to_dict(row)


# ── Connection tests ──────────────────────────────────────────────────

@router.post("/test/smtp", response_model=ConnectionTestResult)
def test_smtp_connection(db=Depends(get_session)):
    """Test SMTP connectivity using current effective config (DB > env)."""
    result = test_smtp(db)
    return result


@router.post("/test/imap", response_model=ConnectionTestResult)
def test_imap_connection(db=Depends(get_session)):
    """Test IMAP connectivity using current effective config (DB > env)."""
    result = test_imap(db)
    return result


@router.post("/test/kapso")
def test_kapso_connection(db=Depends(get_session)):
    """Test Kapso API connectivity."""
    from app.core.config import settings as app_settings
    if not app_settings.KAPSO_API_KEY:
        return {"status": "error", "message": "KAPSO_API_KEY no configurada en .env"}
    try:
        import httpx
        # GET /whatsapp_messages returns 404 (POST-only) but proves connectivity + auth
        resp = httpx.get(
            f"{app_settings.KAPSO_BASE_URL}/whatsapp_messages",
            headers={"X-API-Key": app_settings.KAPSO_API_KEY},
            timeout=10,
        )
        if resp.status_code in (401, 403):
            return {"status": "error", "message": "API key inválida o sin permisos"}
        # Any response (including 404/405) means Kapso is reachable and key is accepted
        return {"status": "ok", "message": "Conexión con Kapso exitosa"}
    except httpx.ConnectError:
        return {"status": "error", "message": "No se pudo conectar a Kapso"}
    except Exception as exc:
        return {"status": "error", "message": f"Error de conexión: {exc}"}


# ── Setup / readiness checklist ───────────────────────────────────────

@router.get("/setup-status", response_model=SetupStatusResponse)
def setup_status(db=Depends(get_session)):
    """Return actionable setup checklist and readiness state."""
    return get_setup_status(db)


# ── Legacy: credential presence (env-only) ────────────────────────────

@router.get("/credentials", response_model=CredentialsStatusResponse)
def credentials_status():
    """Return presence-only status for secret env vars. Values never exposed."""
    smtp_items = [
        CredentialStatusItem(
            key="MAIL_SMTP_HOST",
            label="SMTP Host",
            set=bool((env.MAIL_SMTP_HOST or "").strip()),
            required=True,
        ),
        CredentialStatusItem(
            key="MAIL_SMTP_USERNAME",
            label="SMTP Username",
            set=bool((env.MAIL_SMTP_USERNAME or "").strip()),
            required=True,
        ),
        CredentialStatusItem(
            key="MAIL_SMTP_PASSWORD",
            label="SMTP Password",
            set=bool((env.MAIL_SMTP_PASSWORD or "").strip()),
            required=True,
        ),
        CredentialStatusItem(
            key="MAIL_FROM_EMAIL",
            label="From Email",
            set=bool((env.MAIL_FROM_EMAIL or "").strip()),
            required=True,
        ),
    ]
    imap_items = [
        CredentialStatusItem(
            key="MAIL_IMAP_HOST",
            label="IMAP Host",
            set=bool((env.MAIL_IMAP_HOST or "").strip()),
            required=True,
        ),
        CredentialStatusItem(
            key="MAIL_IMAP_USERNAME",
            label="IMAP Username",
            set=bool((env.MAIL_IMAP_USERNAME or "").strip()),
            required=True,
        ),
        CredentialStatusItem(
            key="MAIL_IMAP_PASSWORD",
            label="IMAP Password",
            set=bool((env.MAIL_IMAP_PASSWORD or "").strip()),
            required=True,
        ),
    ]
    return CredentialsStatusResponse(
        smtp=smtp_items,
        imap=imap_items,
        all_smtp_ready=all(item.set for item in smtp_items if item.required),
        all_imap_ready=all(item.set for item in imap_items if item.required),
        kapso_api_key=bool(env.KAPSO_API_KEY),
    )


# ── WhatsApp credentials and test ─────────────────────────────────────

from app.schemas.whatsapp import WhatsAppCredentialsResponse, WhatsAppCredentialsUpdate, WhatsAppTestResult
from app.services.whatsapp_service import (
    get_credentials as get_wa_creds,
    update_credentials as update_wa_creds,
    to_response_dict as wa_to_dict,
    test_whatsapp,
)


@router.get('/whatsapp-credentials', response_model=WhatsAppCredentialsResponse)
def get_whatsapp_credentials(db=Depends(get_session)):
    row = get_wa_creds(db)
    return wa_to_dict(row)


@router.patch('/whatsapp-credentials', response_model=WhatsAppCredentialsResponse)
def patch_whatsapp_credentials(body: WhatsAppCredentialsUpdate, db=Depends(get_session)):
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail='No fields to update provided.')
    row = update_wa_creds(db, updates)
    return wa_to_dict(row)


@router.post('/test/whatsapp', response_model=WhatsAppTestResult)
def test_whatsapp_connection(db=Depends(get_session)):
    return test_whatsapp(db)


# ── Telegram credentials and test ────────────────────────────────────

from app.schemas.telegram import TelegramCredentialsResponse, TelegramCredentialsUpdate, TelegramTestResult
from app.services.telegram_service import (
    get_credentials as get_tg_creds,
    update_credentials as update_tg_creds,
    to_response_dict as tg_to_dict,
    test_telegram,
)


@router.get('/telegram-credentials', response_model=TelegramCredentialsResponse)
def get_telegram_credentials(db=Depends(get_session)):
    row = get_tg_creds(db)
    return tg_to_dict(row)


@router.patch('/telegram-credentials', response_model=TelegramCredentialsResponse)
def patch_telegram_credentials(body: TelegramCredentialsUpdate, db=Depends(get_session)):
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail='No fields to update provided.')
    row = update_tg_creds(db, updates)
    return tg_to_dict(row)


@router.post('/test/telegram', response_model=TelegramTestResult)
def test_telegram_connection(db=Depends(get_session)):
    return test_telegram(db)


from pydantic import BaseModel as _BaseModel


class TelegramRegisterWebhookBody(_BaseModel):
    webhook_url: str


@router.post('/telegram/register-webhook')
def register_telegram_webhook(body: TelegramRegisterWebhookBody, db=Depends(get_session)):
    """Register the webhook URL with Telegram Bot API and auto-generate a secret."""
    import secrets as _secrets
    from app.services.telegram_service import _call_telegram

    creds = get_tg_creds(db)
    if not creds.bot_token:
        raise HTTPException(status_code=400, detail="No hay bot token configurado.")

    # Generate a webhook secret if not set
    webhook_secret = creds.webhook_secret
    if not webhook_secret:
        webhook_secret = _secrets.token_urlsafe(32)

    # Register with Telegram
    try:
        result = _call_telegram(creds.bot_token, "setWebhook", {
            "url": body.webhook_url,
            "secret_token": webhook_secret,
            "allowed_updates": ["message", "edited_message"],
        })
        if not result.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=f"Telegram API error: {result.get('description', 'unknown')}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("telegram_webhook_register_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Error al registrar webhook. Revisá los logs.")

    # Save webhook_url and secret to DB
    update_tg_creds(db, {
        "webhook_url": body.webhook_url,
        "webhook_secret": webhook_secret,
    })

    return {
        "ok": True,
        "message": f"Webhook registrado en {body.webhook_url}",
        "webhook_secret": webhook_secret,
    }


# ── OpenClaw WhatsApp automation ──────────────────────────────────────

import json
import subprocess
import shutil
from pathlib import Path


class OpenClawStatusResponse(_BaseModel):
    installed: bool
    version: str | None = None
    config_exists: bool
    whatsapp_configured: bool
    whatsapp_linked: bool
    gateway_running: bool
    phone_number: str | None = None
    allowed_numbers: list[str] = []


class OpenClawSetupBody(_BaseModel):
    phone_number: str


_OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


def _find_openclaw_bin() -> str | None:
    """Find openclaw binary in PATH or common install locations."""
    found = shutil.which("openclaw")
    if found:
        return found
    # Check common locations when not in PATH
    home = Path.home()
    for candidate in [
        home / ".openclaw" / "bin" / "openclaw",
        home / ".local" / "bin" / "openclaw",
        Path("/usr/local/bin/openclaw"),
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def _read_openclaw_config() -> dict | None:
    if _OPENCLAW_CONFIG.exists():
        try:
            return json.loads(_OPENCLAW_CONFIG.read_text())
        except Exception:
            return None
    return None


def _has_whatsapp_channel(config: dict | None) -> bool:
    if not config:
        return False
    channels = config.get("channels", {})
    return "whatsapp" in channels


def _is_gateway_running() -> bool:
    oc = _find_openclaw_bin()
    if not oc:
        return False
    try:
        r = subprocess.run(
            [oc, "gateway", "status"],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and "running" in r.stdout.lower()
    except Exception:
        return False


def _is_whatsapp_linked() -> bool:
    """Check if WhatsApp is actually linked by asking OpenClaw directly."""
    oc = _find_openclaw_bin()
    if not oc:
        return False
    try:
        r = subprocess.run(
            [oc, "channels", "status"],
            capture_output=True, text=True, timeout=10,
        )
        # Look for "not linked" in the output — if present, it's NOT linked
        output = r.stdout.lower()
        if "whatsapp" in output and "not linked" in output:
            return False
        # If whatsapp is mentioned without "not linked", it's linked
        if "whatsapp" in output and "linked" in output:
            return True
        return False
    except Exception:
        return False


@router.get('/openclaw/status', response_model=OpenClawStatusResponse)
def get_openclaw_status():
    """Check OpenClaw installation and WhatsApp status."""
    oc = _find_openclaw_bin()
    version: str | None = None
    if oc:
        try:
            r = subprocess.run([oc, "--version"], capture_output=True, text=True, timeout=5)
            version = r.stdout.strip().split("\n")[0] if r.returncode == 0 else None
        except Exception:
            pass

    config = _read_openclaw_config()
    wa_config = config.get("channels", {}).get("whatsapp", {}) if config else {}
    allowed = wa_config.get("allowFrom", [])

    return OpenClawStatusResponse(
        installed=oc is not None,
        version=version,
        config_exists=config is not None,
        whatsapp_configured=_has_whatsapp_channel(config),
        whatsapp_linked=_is_whatsapp_linked(),
        gateway_running=_is_gateway_running(),
        allowed_numbers=allowed,
    )


@router.post('/openclaw/setup-whatsapp')
def setup_openclaw_whatsapp(body: OpenClawSetupBody):
    """Add WhatsApp channel to OpenClaw config with the given phone number."""
    config = _read_openclaw_config()
    if config is None:
        raise HTTPException(status_code=404, detail="OpenClaw config no encontrado en ~/.openclaw/openclaw.json")

    # Add or update WhatsApp channel
    if "channels" not in config:
        config["channels"] = {}

    phone = body.phone_number.strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"

    config["channels"]["whatsapp"] = {
        "dmPolicy": "allowlist",
        "allowFrom": [phone],
    }

    # Backup and write
    import shutil as _shutil
    if _OPENCLAW_CONFIG.exists():
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _shutil.copy2(_OPENCLAW_CONFIG, _OPENCLAW_CONFIG.with_suffix(f".bak.{ts}"))

    _OPENCLAW_CONFIG.write_text(json.dumps(config, indent=2))

    # Run doctor --fix to enable the channel properly
    oc = _find_openclaw_bin()
    if oc:
        try:
            subprocess.run(
                [oc, "doctor", "--fix"],
                capture_output=True, text=True, timeout=30,
            )
        except Exception:
            pass  # Best-effort

    return {
        "ok": True,
        "message": f"WhatsApp configurado para {phone}",
        "config_path": str(_OPENCLAW_CONFIG),
    }



def _ensure_gateway_ready(oc: str) -> None:
    """Install gateway service if needed and start it."""
    # Check if already running
    if _is_gateway_running():
        return
    # Install service (idempotent — reinstalls if already installed)
    subprocess.run(
        [oc, "gateway", "install"],
        capture_output=True, text=True, timeout=30,
    )
    # Run doctor --fix to enable channels properly
    subprocess.run(
        [oc, "doctor", "--fix"],
        capture_output=True, text=True, timeout=30,
    )
    # Start the service
    subprocess.run(
        [oc, "gateway", "start"],
        capture_output=True, text=True, timeout=15,
    )


@router.post('/openclaw/link-whatsapp')
def link_openclaw_whatsapp():
    """Open a terminal window with the WhatsApp login command (QR scan)."""
    oc = _find_openclaw_bin()
    if not oc:
        raise HTTPException(status_code=404, detail="OpenClaw no encontrado")

    # Ensure gateway service is installed, doctor has run, and gateway is up
    try:
        _ensure_gateway_ready(oc)
    except Exception:
        pass  # Best-effort

    try:
        # Write a temp script to avoid quoting issues with wt.exe
        script = Path("/tmp/openclaw_wa_login.sh")
        script.write_text(
            f'#!/bin/bash\n'
            f'echo ""\n'
            f'echo "Escaneá el QR con WhatsApp > Dispositivos vinculados > Vincular dispositivo"\n'
            f'echo ""\n'
            f'{oc} channels login --channel whatsapp\n'
            f'echo ""\n'
            f'echo "Listo. Podes cerrar esta ventana."\n'
            f'read -r -p "Presiona Enter para cerrar..."\n'
        )
        script.chmod(0o755)

        # Try to open Windows Terminal (wt.exe) from WSL
        try:
            subprocess.Popen(
                ["wt.exe", "-w", "0", "nt", "wsl", "bash", str(script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return {"ok": True, "method": "terminal", "message": "Terminal abierta — escaneá el QR en la ventana."}
        except FileNotFoundError:
            pass

        # Fallback: try Linux terminal emulators
        for term_cmd in [
            ["x-terminal-emulator", "-e", f"bash {script}"],
            ["gnome-terminal", "--", "bash", str(script)],
            ["xterm", "-e", f"bash {script}"],
        ]:
            try:
                subprocess.Popen(
                    term_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return {"ok": True, "method": "terminal", "message": "Terminal abierta — escaneá el QR en la ventana."}
            except FileNotFoundError:
                continue

        # No terminal found — return the command for manual copy
        return {
            "ok": True,
            "method": "manual",
            "message": "No se pudo abrir terminal automaticamente.",
            "command": f"{oc} channels login --channel whatsapp",
        }
    except Exception as exc:
        logger.error("openclaw_terminal_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Error al abrir terminal. Revisá los logs.")


@router.post('/openclaw/start-gateway')
def start_openclaw_gateway():
    """Start the OpenClaw gateway via systemd service."""
    oc = _find_openclaw_bin()
    if not oc:
        raise HTTPException(status_code=404, detail="OpenClaw no encontrado en PATH")

    if _is_gateway_running():
        return {"ok": True, "message": "El gateway ya esta corriendo."}

    try:
        _ensure_gateway_ready(oc)
        # Verify it actually started
        import time
        time.sleep(2)
        if _is_gateway_running():
            return {
                "ok": True,
                "message": "Gateway iniciado. OpenClaw esta escuchando mensajes de WhatsApp.",
            }
        return {
            "ok": False,
            "message": "Gateway instalado pero no confirmo inicio. Verifica con 'openclaw gateway status'.",
        }
    except Exception as exc:
        logger.error("openclaw_gateway_start_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Error al iniciar gateway. Revisá los logs.")


# ── AI Workspace (OpenClaw config files) ──────────────────────────────

from app.schemas.ai_workspace import (
    AIWorkspaceFileContent,
    AIWorkspaceFileResetResponse,
    AIWorkspaceFileUpdate,
    AIWorkspaceStatusResponse,
)
from app.services.ai_workspace_service import (
    get_file_content as _ws_get_file,
    get_workspace_status as _ws_status,
    reset_file_to_template as _ws_reset,
    update_file_content as _ws_update,
    EDITABLE_KEYS,
    WORKSPACE_FILES,
)


@router.get("/ai-workspace", response_model=AIWorkspaceStatusResponse)
def ai_workspace_status():
    """Return status of all AI workspace configuration files."""
    return _ws_status()


@router.get("/ai-workspace/{key}", response_model=AIWorkspaceFileContent)
def ai_workspace_get_file(key: str):
    """Return the full content of an AI workspace file."""
    if key not in WORKSPACE_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown workspace file key: {key}")
    if key not in EDITABLE_KEYS:
        raise HTTPException(status_code=403, detail=f"File '{key}' is not editable (framework-managed)")
    return _ws_get_file(key)


@router.put("/ai-workspace/{key}", response_model=AIWorkspaceFileContent)
def ai_workspace_update_file(key: str, body: AIWorkspaceFileUpdate):
    """Write content to an AI workspace file."""
    if key not in WORKSPACE_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown workspace file key: {key}")
    if key not in EDITABLE_KEYS:
        raise HTTPException(status_code=403, detail=f"File '{key}' is not editable (framework-managed)")
    try:
        return _ws_update(key, body.content)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/ai-workspace/{key}/reset", response_model=AIWorkspaceFileResetResponse)
def ai_workspace_reset_file(key: str):
    """Reset an AI workspace file to its default template."""
    if key not in WORKSPACE_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown workspace file key: {key}")
    if key not in EDITABLE_KEYS:
        raise HTTPException(status_code=403, detail=f"File '{key}' is not editable (framework-managed)")
    try:
        return _ws_reset(key)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
