from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_session
from app.core.config import settings as env
from app.schemas.operational_settings import (
    CredentialStatusItem,
    CredentialsStatusResponse,
    OperationalSettingsResponse,
    OperationalSettingsUpdate,
)
from app.schemas.settings import LLMSettingsResponse, MailSettingsResponse
from app.services.operational_settings_service import (
    get_or_create,
    to_response_dict,
    update_operational_settings,
)
from app.services.settings_service import get_llm_settings, get_mail_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMSettingsResponse)
def llm_settings():
    """Return the active LLM configuration (read-only from env)."""
    return get_llm_settings()


@router.get("/mail", response_model=MailSettingsResponse)
def mail_settings(db=Depends(get_session)):
    """Return effective mail settings (DB overrides + env fallback)."""
    return get_mail_settings(db)


@router.get("/operational", response_model=OperationalSettingsResponse)
def get_operational(db=Depends(get_session)):
    """Return the current operational settings (brand, rules, mail overrides)."""
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
