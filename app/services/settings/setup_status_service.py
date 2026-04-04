"""Compute actionable setup/readiness status for the settings checklist."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.outreach.mail_credentials_service import get_effective_imap, get_effective_smtp
from app.services.outreach.mail_credentials_service import get_or_create as get_creds
from app.services.settings.operational_settings_service import get_or_create as get_ops


def _get_wa_creds(db: Session):
    from app.models.whatsapp_credentials import WhatsAppCredentials

    return db.get(WhatsAppCredentials, 1)


def _get_tg_creds(db: Session):
    from app.models.telegram_credentials import TelegramCredentials

    return db.get(TelegramCredentials, 1)


def get_setup_status(db: Session) -> dict:
    ops = get_ops(db)
    creds = get_creds(db)
    smtp = get_effective_smtp(db)
    imap = get_effective_imap(db)
    wa = _get_wa_creds(db)
    tg = _get_tg_creds(db)

    steps = []

    # ── Step 1: Brand & Signature ──────────────────────────────────────
    brand_missing = []
    if not ops.brand_name:
        brand_missing.append("Nombre comercial")
    if not ops.signature_name:
        brand_missing.append("Nombre del firmante")
    if brand_missing:
        steps.append({
            "id": "brand",
            "label": "Marca y firma",
            "status": "incomplete",
            "detail": f"Falta: {', '.join(brand_missing)}",
            "action": "Completar marca",
        })
    else:
        steps.append({
            "id": "brand",
            "label": "Marca y firma",
            "status": "complete",
            "detail": f"{ops.brand_name} · {ops.signature_name}",
            "action": None,
        })

    # ── Step 2: WhatsApp (CallMeBot notifications + Kapso outreach) ───
    wa_has_phone = bool(wa and wa.phone_number)
    wa_has_key = bool(wa and wa.api_key)
    if wa_has_phone and wa_has_key:
        if wa.last_test_ok is None:
            steps.append({
                "id": "whatsapp",
                "label": "WhatsApp",
                "status": "warning",
                "detail": "Credenciales cargadas pero conexión no probada",
                "action": "Probar conexión",
            })
        elif not wa.last_test_ok:
            steps.append({
                "id": "whatsapp",
                "label": "WhatsApp",
                "status": "warning",
                "detail": f"Última prueba falló: {wa.last_test_error or 'error'}",
                "action": "Probar conexión",
            })
        else:
            steps.append({
                "id": "whatsapp",
                "label": "WhatsApp",
                "status": "complete",
                "detail": f"{wa.phone_number} · CallMeBot",
                "action": None,
            })
    else:
        wa_missing = []
        if not wa_has_phone:
            wa_missing.append("número de teléfono")
        if not wa_has_key:
            wa_missing.append("API key")
        steps.append({
            "id": "whatsapp",
            "label": "WhatsApp",
            "status": "incomplete",
            "detail": f"Falta: {', '.join(wa_missing)}",
            "action": "Configurar WhatsApp",
        })

    # ── Step 3: Mail Outbound ─────────────────────────────────────────
    smtp_missing = []
    if not smtp.host:
        smtp_missing.append("servidor SMTP")
    if not smtp.username:
        smtp_missing.append("usuario")
    if not smtp.password:
        smtp_missing.append("contraseña")
    from_email = ops.mail_from_email
    if not from_email:
        smtp_missing.append("dirección de envío (From Email)")

    if smtp_missing:
        steps.append({
            "id": "mail_out",
            "label": "Mail de salida (SMTP)",
            "status": "incomplete",
            "detail": f"Falta: {', '.join(smtp_missing)}",
            "action": "Conectar mail de salida",
        })
    elif creds.smtp_last_test_ok is None:
        steps.append({
            "id": "mail_out",
            "label": "Mail de salida (SMTP)",
            "status": "warning",
            "detail": "Credenciales cargadas pero conexión no probada aún",
            "action": "Probar conexión",
        })
    elif not creds.smtp_last_test_ok:
        steps.append({
            "id": "mail_out",
            "label": "Mail de salida (SMTP)",
            "status": "warning",
            "detail": f"Última prueba falló: {creds.smtp_last_test_error or 'error desconocido'}",
            "action": "Probar conexión",
        })
    else:
        steps.append({
            "id": "mail_out",
            "label": "Mail de salida (SMTP)",
            "status": "complete",
            "detail": f"{smtp.host} · {smtp.username}",
            "action": None,
        })

    # ── Step 4: Mail Inbound ──────────────────────────────────────────
    imap_missing = []
    if not imap.host:
        imap_missing.append("servidor IMAP")
    if not imap.username:
        imap_missing.append("usuario")
    if not imap.password:
        imap_missing.append("contraseña")

    if imap_missing:
        steps.append({
            "id": "mail_in",
            "label": "Bandeja de entrada (IMAP)",
            "status": "incomplete",
            "detail": f"Falta: {', '.join(imap_missing)}",
            "action": "Conectar bandeja de entrada",
        })
    elif creds.imap_last_test_ok is None:
        steps.append({
            "id": "mail_in",
            "label": "Bandeja de entrada (IMAP)",
            "status": "warning",
            "detail": "Credenciales cargadas pero conexión no probada aún",
            "action": "Probar conexión",
        })
    elif not creds.imap_last_test_ok:
        steps.append({
            "id": "mail_in",
            "label": "Bandeja de entrada (IMAP)",
            "status": "warning",
            "detail": f"Última prueba falló: {creds.imap_last_test_error or 'error desconocido'}",
            "action": "Probar conexión",
        })
    else:
        steps.append({
            "id": "mail_in",
            "label": "Bandeja de entrada (IMAP)",
            "status": "complete",
            "detail": f"{imap.host} · {imap.username}",
            "action": None,
        })

    # ── Step 5: Telegram notifications ────────────────────────────────
    tg_has_token = bool(tg and tg.bot_token)
    tg_has_chat = bool(tg and tg.chat_id)
    if tg_has_token and tg_has_chat:
        if tg.last_test_ok is None:
            steps.append({
                "id": "telegram",
                "label": "Telegram",
                "status": "warning",
                "detail": "Bot configurado pero conexión no probada",
                "action": "Probar conexión",
            })
        elif not tg.last_test_ok:
            steps.append({
                "id": "telegram",
                "label": "Telegram",
                "status": "warning",
                "detail": f"Última prueba falló: {tg.last_test_error or 'error'}",
                "action": "Probar conexión",
            })
        else:
            steps.append({
                "id": "telegram",
                "label": "Telegram",
                "status": "complete",
                "detail": f"@{tg.bot_username or 'bot'} · chat {tg.chat_id}",
                "action": None,
            })
    else:
        tg_missing = []
        if not tg_has_token:
            tg_missing.append("bot token")
        if not tg_has_chat:
            tg_missing.append("chat ID")
        steps.append({
            "id": "telegram",
            "label": "Telegram",
            "status": "incomplete",
            "detail": f"Falta: {', '.join(tg_missing)}",
            "action": "Configurar Telegram",
        })

    # ── Step 6: Rules ─────────────────────────────────────────────────
    steps.append({
        "id": "rules",
        "label": "Reglas operativas",
        "status": "complete",
        "detail": "Usando configuración por defecto",
        "action": None,
    })

    # ── Compute overall ───────────────────────────────────────────────
    statuses = [s["status"] for s in steps]
    ready_to_send = (
        bool(smtp.host and smtp.username and smtp.password and ops.mail_from_email)
        and creds.smtp_last_test_ok is True
    )
    ready_to_receive = (
        bool(imap.host and imap.username and imap.password)
        and creds.imap_last_test_ok is True
    )

    # At least one outreach channel configured (WhatsApp OR Email)
    wa_step = next((s for s in steps if s["id"] == "whatsapp"), None)
    mail_step = next((s for s in steps if s["id"] == "mail_out"), None)
    has_outreach_channel = (
        (wa_step and wa_step["status"] != "incomplete")
        or (mail_step and mail_step["status"] != "incomplete")
    )

    if "incomplete" in statuses:
        overall = "incomplete"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "ready"

    return {
        "steps": steps,
        "overall": overall,
        "ready_to_send": ready_to_send,
        "ready_to_receive": ready_to_receive,
        "has_outreach_channel": has_outreach_channel,
    }
