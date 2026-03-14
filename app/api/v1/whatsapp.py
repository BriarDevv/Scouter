"""WhatsApp webhook — inbound message endpoint for conversational queries."""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.logging import get_logger
from app.models.settings import OperationalSettings
from app.services.whatsapp_audit import log_inbound, log_outbound
from app.services.whatsapp_conversation import Intent, _detect_intent, _sanitize, handle_inbound_message
from app.services.whatsapp_service import send_alert

logger = get_logger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])




class InboundMessageBody(BaseModel):
    phone: str
    message: str
    provider: str = "callmebot"


class WebhookResponse(BaseModel):
    ok: bool
    response: str


def _get_settings(db: Session) -> OperationalSettings:
    """Retrieve the singleton operational settings row."""
    row = db.get(OperationalSettings, 1)
    if not row:
        row = OperationalSettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/webhook")
def webhook_verify(
    challenge: str = Query("", alias="hub.challenge"),
) -> dict:
    """Verification endpoint for Meta/Twilio webhook setup."""
    return {"challenge": challenge}


@router.post("/webhook", response_model=WebhookResponse)
def webhook_inbound(
    body: InboundMessageBody,
    db: Session = Depends(get_session),
    x_webhook_secret: str = Header("", alias="X-Webhook-Secret"),
) -> WebhookResponse:
    """Receive inbound WhatsApp messages and return a conversational response."""
    # Validate webhook secret
    webhook_secret = os.environ.get("WHATSAPP_WEBHOOK_SECRET", "")
    if not webhook_secret or x_webhook_secret != webhook_secret:
        logger.warning("wa_webhook_auth_failed", phone=body.phone[:6] + "***")
        raise HTTPException(status_code=403, detail="Webhook secret invalido.")

    # Check feature flag
    settings = _get_settings(db)
    if not settings.whatsapp_conversational_enabled:
        logger.info("wa_conversational_disabled")
        raise HTTPException(
            status_code=403,
            detail="La funcion de WhatsApp conversacional no esta habilitada.",
        )

    # Process message
    start = time.monotonic()
    response_text = handle_inbound_message(db, body.phone, body.message)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Detect intent for audit
    clean = _sanitize(body.message)
    intent_name: str | None = None
    if clean:
        intent, _ = _detect_intent(clean)
        intent_name = intent.value

    # Audit log
    log_inbound(db, body.phone, body.message, intent_name)
    log_outbound(db, body.phone, response_text, elapsed_ms)

    # Send response back via WhatsApp (best-effort, don't fail the webhook)
    try:
        send_alert(
            db,
            title="Respuesta",
            message=response_text,
            severity="info",
        )
    except Exception:
        logger.exception("wa_send_response_failed", phone=body.phone[:6] + "***")

    logger.info(
        "wa_webhook_processed",
        phone=body.phone[:6] + "***",
        intent=intent_name,
        latency_ms=elapsed_ms,
    )

    return WebhookResponse(ok=True, response=response_text)
