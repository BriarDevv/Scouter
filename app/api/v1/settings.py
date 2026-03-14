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
