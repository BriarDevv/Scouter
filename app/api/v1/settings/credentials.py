from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings as app_settings
from app.db.session import get_db
from app.schemas.mail_credentials import (
    ConnectionTestResult,
    MailCredentialsResponse,
    MailCredentialsUpdate,
)
from app.services.deploy_config_service import (
    InvalidKapsoKeyError,
    get_effective_kapso_api_key,
    get_kapso_api_key_status,
    set_kapso_api_key,
)
from app.services.outreach.mail_credentials_service import (
    get_or_create as get_creds,
)
from app.services.outreach.mail_credentials_service import (
    test_imap,
    test_smtp,
    update_credentials,
)
from app.services.outreach.mail_credentials_service import (
    to_response_dict as creds_to_dict,
)

router = APIRouter()
DbSession = Annotated[object, Depends(get_db)]


@router.get("/mail-credentials", response_model=MailCredentialsResponse)
def get_mail_credentials(db: DbSession):
    """Return mail connection settings. Passwords never exposed."""
    row = get_creds(db)
    return creds_to_dict(row)


@router.patch("/mail-credentials", response_model=MailCredentialsResponse)
def patch_mail_credentials(body: MailCredentialsUpdate, db: DbSession):
    """Update mail connection settings. Include password only when changing it."""
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update provided.")
    row = update_credentials(db, updates)
    db.commit()
    return creds_to_dict(row)


@router.post("/test/smtp", response_model=ConnectionTestResult)
def test_smtp_connection(db: DbSession):
    """Test SMTP connectivity using current effective config (DB > env).

    Persists the test outcome (smtp_last_test_at/ok/error) so the setup
    checklist reflects the latest state without the operator having to
    save credentials again.
    """
    result = test_smtp(db)
    db.commit()
    return result


@router.post("/test/imap", response_model=ConnectionTestResult)
def test_imap_connection(db: DbSession):
    """Test IMAP connectivity using current effective config (DB > env).

    Persists the test outcome (imap_last_test_at/ok/error) so the setup
    checklist reflects the latest state without the operator having to
    save credentials again.
    """
    result = test_imap(db)
    db.commit()
    return result


@router.post("/test/kapso")
def test_kapso_connection(db: DbSession):
    """Test Kapso API connectivity using effective key (DB > env)."""
    effective_key = get_effective_kapso_api_key(db)
    if not effective_key:
        return {"status": "error", "message": "KAPSO_API_KEY no configurada"}
    try:
        resp = httpx.get(
            f"{app_settings.KAPSO_BASE_URL}/whatsapp_messages",
            headers={"X-API-Key": effective_key},
            timeout=10,
        )
        if resp.status_code in (401, 403):
            return {"status": "error", "message": "API key inválida o sin permisos"}
        return {"status": "ok", "message": "Conexión con Kapso exitosa"}
    except httpx.ConnectError:
        return {"status": "error", "message": "No se pudo conectar a Kapso"}
    except Exception as exc:
        return {"status": "error", "message": f"Error de conexión: {exc}"}


# ── Kapso API key ─────────────────────────────────────────────────────


class KapsoApiKeyUpdate(BaseModel):
    api_key: str


@router.get("/kapso-credentials")
def get_kapso_credentials(db: DbSession):
    """Return Kapso API key status (never exposes raw key)."""
    return get_kapso_api_key_status(db)


@router.patch("/kapso-credentials")
def patch_kapso_credentials(body: KapsoApiKeyUpdate, db: DbSession):
    """Persist a Kapso API key encrypted in DB. DB value wins over .env."""
    try:
        status = set_kapso_api_key(db, body.api_key)
    except InvalidKapsoKeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return status
