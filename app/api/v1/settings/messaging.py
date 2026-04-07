import secrets as _secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db.session import get_db
from app.core.logging import get_logger
from app.schemas.telegram import (
    TelegramCredentialsResponse,
    TelegramCredentialsUpdate,
    TelegramTestResult,
)
from app.schemas.whatsapp import (
    WhatsAppCredentialsResponse,
    WhatsAppCredentialsUpdate,
    WhatsAppTestResult,
)
from app.services.comms.telegram_service import (
    _call_telegram,
    test_telegram,
)
from app.services.comms.telegram_service import (
    get_credentials as get_tg_creds,
)
from app.services.comms.telegram_service import (
    to_response_dict as tg_to_dict,
)
from app.services.comms.telegram_service import (
    update_credentials as update_tg_creds,
)
from app.services.comms.whatsapp_service import (
    get_credentials as get_wa_creds,
)
from app.services.comms.whatsapp_service import (
    test_whatsapp,
)
from app.services.comms.whatsapp_service import (
    to_response_dict as wa_to_dict,
)
from app.services.comms.whatsapp_service import (
    update_credentials as update_wa_creds,
)

logger = get_logger(__name__)
router = APIRouter()
DbSession = Annotated[object, Depends(get_db)]


@router.get("/whatsapp-credentials", response_model=WhatsAppCredentialsResponse)
def get_whatsapp_credentials(db: DbSession):
    row = get_wa_creds(db)
    db.commit()
    return wa_to_dict(row)


@router.patch("/whatsapp-credentials", response_model=WhatsAppCredentialsResponse)
def patch_whatsapp_credentials(body: WhatsAppCredentialsUpdate, db: DbSession):
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update provided.")
    row = update_wa_creds(db, updates)
    db.commit()
    return wa_to_dict(row)


@router.post("/test/whatsapp", response_model=WhatsAppTestResult)
def test_whatsapp_connection(db: DbSession):
    result = test_whatsapp(db)
    db.commit()
    return result


@router.get("/telegram-credentials", response_model=TelegramCredentialsResponse)
def get_telegram_credentials(db: DbSession):
    row = get_tg_creds(db)
    db.commit()
    return tg_to_dict(row)


@router.patch("/telegram-credentials", response_model=TelegramCredentialsResponse)
def patch_telegram_credentials(body: TelegramCredentialsUpdate, db: DbSession):
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update provided.")
    row = update_tg_creds(db, updates)
    db.commit()
    return tg_to_dict(row)


@router.post("/test/telegram", response_model=TelegramTestResult)
def test_telegram_connection(db: DbSession):
    result = test_telegram(db)
    db.commit()
    return result


class TelegramRegisterWebhookBody(BaseModel):
    webhook_url: str


@router.post("/telegram/register-webhook")
def register_telegram_webhook(
    body: TelegramRegisterWebhookBody,
    db: DbSession,
):
    """Register the webhook URL with Telegram Bot API and auto-generate a secret."""
    creds = get_tg_creds(db)
    if not creds.bot_token:
        raise HTTPException(status_code=400, detail="No hay bot token configurado.")

    webhook_secret = creds.webhook_secret or _secrets.token_urlsafe(32)

    try:
        result = _call_telegram(
            creds.bot_token,
            "setWebhook",
            {
                "url": body.webhook_url,
                "secret_token": webhook_secret,
                "allowed_updates": ["message", "edited_message"],
            },
        )
        if not result.get("ok"):
            raise HTTPException(
                status_code=502,
                detail=f"Telegram API error: {result.get('description', 'unknown')}",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("telegram_webhook_register_failed", error=str(exc))
        raise HTTPException(
            status_code=502,
            detail="Error al registrar webhook. Revisá los logs.",
        ) from exc

    update_tg_creds(
        db,
        {
            "webhook_url": body.webhook_url,
            "webhook_secret": webhook_secret,
        },
    )
    db.commit()

    return {
        "ok": True,
        "message": f"Webhook registrado en {body.webhook_url}",
        "webhook_secret": webhook_secret,
    }
