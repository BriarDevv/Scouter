"""WhatsApp webhook — routes inbound messages through the Hermes 3 agent."""

from __future__ import annotations

import hmac
import os
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.channel_router import handle_channel_message
from app.core.logging import get_logger
from app.db.session import get_db
from app.services.comms.whatsapp_audit import log_inbound, log_outbound
from app.services.comms.whatsapp_service import send_alert
from app.services.settings.operational_settings_service import get_or_create as get_settings

logger = get_logger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class InboundMessageBody(BaseModel):
    phone: str = Field(..., max_length=50)
    message: str = Field(..., max_length=4096)
    provider: str = "callmebot"


class WebhookResponse(BaseModel):
    ok: bool
    response: str


@router.get("/webhook")
def webhook_verify(challenge: str = Query("", alias="hub.challenge")) -> dict:
    """Verification endpoint for Meta/Twilio webhook setup."""
    return {"challenge": challenge}


@router.post("/webhook", response_model=WebhookResponse)
def webhook_inbound(
    body: InboundMessageBody,
    db: Session = Depends(get_db),
    x_webhook_secret: str = Header("", alias="X-Webhook-Secret"),
) -> WebhookResponse:
    """Receive WhatsApp messages, process via Hermes 3 agent, send response."""
    # Validate webhook secret
    from app.models.whatsapp_credentials import WhatsAppCredentials

    wa_creds = db.get(WhatsAppCredentials, 1)
    webhook_secret = (
        wa_creds.webhook_secret if wa_creds and wa_creds.webhook_secret else None
    ) or os.environ.get("WHATSAPP_WEBHOOK_SECRET", "")
    if not webhook_secret or not hmac.compare_digest(x_webhook_secret, webhook_secret):
        logger.warning("wa_webhook_auth_failed", phone=body.phone[:6] + "***")
        raise HTTPException(status_code=403, detail="Webhook secret invalido.")

    # Check feature flag
    settings = get_settings(db)
    if not getattr(settings, "whatsapp_agent_enabled", False):
        logger.info("wa_agent_disabled")
        raise HTTPException(status_code=403, detail="WhatsApp agent no habilitado.")

    # Process via Hermes 3 agent
    start = time.monotonic()
    response_text = handle_channel_message(
        db=db,
        channel="whatsapp",
        channel_id=body.phone,
        message=body.message,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Audit
    log_inbound(db, body.phone, body.message, "agent")
    log_outbound(db, body.phone, response_text, elapsed_ms)

    # Send response
    try:
        send_alert(db, title="Respuesta", message=response_text, severity="info")
    except Exception:
        logger.exception("wa_send_response_failed", phone=body.phone[:6] + "***")

    logger.info("wa_webhook_processed", phone=body.phone[:6] + "***", latency_ms=elapsed_ms)
    return WebhookResponse(ok=True, response=response_text)
