from typing import Annotated

from fastapi import APIRouter, Depends

from app.db.session import get_db
from app.core.config import settings as env
from app.schemas.mail_credentials import SetupStatusResponse
from app.schemas.operational_settings import (
    CredentialsStatusResponse,
    CredentialStatusItem,
)
from app.schemas.settings import LLMSettingsResponse, MailSettingsResponse
from app.services.settings.settings_service import get_llm_settings, get_mail_settings
from app.services.settings.setup_status_service import get_setup_status

router = APIRouter()
DbSession = Annotated[object, Depends(get_db)]


@router.get("/llm", response_model=LLMSettingsResponse)
def llm_settings():
    """Return the active LLM configuration (read-only from env)."""
    return get_llm_settings()


@router.get("/mail", response_model=MailSettingsResponse)
def mail_settings(db: DbSession):
    """Return effective mail settings (DB overrides + env fallback)."""
    return get_mail_settings(db)


@router.get("/setup-status", response_model=SetupStatusResponse)
def setup_status(db: DbSession):
    """Return actionable setup checklist and readiness state."""
    return get_setup_status(db)


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
