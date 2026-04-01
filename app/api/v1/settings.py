from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_session
from app.core.config import settings as env
from app.core.logging import get_logger

logger = get_logger(__name__)
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
