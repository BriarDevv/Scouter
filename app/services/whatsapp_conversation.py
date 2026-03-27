"""WhatsApp conversation handler -- query interface + controlled actions via WhatsApp.

Processes inbound messages, detects intent via keyword matching,
and returns formatted plain-text responses suitable for WhatsApp.
Action intents require explicit confirmation before execution (Etapa 3).
"""

from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.notification import Notification, NotificationStatus
from app.models.outreach import DraftStatus, OutreachDraft

logger = get_logger(__name__)

# -- Rate limiting state (in-memory, resets on restart) --
_rate_window: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 20
_RATE_WINDOW_SECONDS = 900  # 15 minutes

# -- SQL / prompt injection patterns to reject --
_SUSPICIOUS_PATTERNS = re.compile(
    r"(drop\s+table|delete\s+from|insert\s+into|update\s+\w+\s+set|"
    r"union\s+select|;--|<script|javascript:|ignore\s+previous|"
    r"system\s*prompt|\\x[0-9a-f]{2})",
    re.IGNORECASE,
)

# -- HTML tag stripper --
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class Intent(str, Enum):
    # Read-only intents (Etapa 2)
    QUERY_LEADS = "query_leads"
    QUERY_LEAD_DETAIL = "query_lead_detail"
    QUERY_NOTIFICATIONS = "query_notifications"
    QUERY_DRAFTS = "query_drafts"
    QUERY_STATS = "query_stats"
    HELP = "help"

    # Action intents (Etapa 3)
    RESOLVE_NOTIFICATION = "resolve_notification"
    MARK_READ_NOTIFICATIONS = "mark_read_notifications"
    APPROVE_DRAFT = "approve_draft"
    REJECT_DRAFT = "reject_draft"
    GENERATE_DRAFT = "generate_draft"


# Set of intents that are actions (require confirmation)
_ACTION_INTENTS = {
    Intent.RESOLVE_NOTIFICATION,
    Intent.MARK_READ_NOTIFICATIONS,
    Intent.APPROVE_DRAFT,
    Intent.REJECT_DRAFT,
    Intent.GENERATE_DRAFT,
}


def _sanitize(text: str) -> str | None:
    """Sanitize input: strip HTML, limit length, reject suspicious content.

    Returns the sanitized string or None if the message should be rejected.
    """
    # Check suspicious patterns on raw input before stripping HTML
    if _SUSPICIOUS_PATTERNS.search(text):
        return None
    text = _HTML_TAG_RE.sub("", text)
    text = text.strip()[:500]
    return text


def _check_rate_limit(phone: str, db: Session | None = None) -> bool:
    """Return True if the phone is within the rate limit window.

    If a db session is provided, reads rate-limit settings from
    OperationalSettings; otherwise falls back to module-level defaults.
    """
    rate_limit = _RATE_LIMIT
    rate_window_seconds = _RATE_WINDOW_SECONDS

    if db is not None:
        from app.models.settings import OperationalSettings
        ops = db.get(OperationalSettings, 1)
        if ops is not None:
            rate_limit = ops.openclaw_rate_limit
            rate_window_seconds = ops.openclaw_rate_window_seconds

    now = time.time()
    window = _rate_window[phone]
    # Prune old entries
    _rate_window[phone] = [t for t in window if now - t < rate_window_seconds]
    if len(_rate_window[phone]) >= rate_limit:
        return False
    _rate_window[phone].append(now)
    return True


def _detect_intent(message: str) -> tuple[Intent, str | None]:
    """Detect intent from message text using keyword matching.

    Returns (intent, extra_arg) where extra_arg is e.g. a lead name/id.
    """
    msg = message.lower().strip()

    # Help
    if msg in ("help", "ayuda", "?"):
        return Intent.HELP, None

    # -- Action intents (Etapa 3) --

    # Resolve notification: "resolver #<id>" or "resolve #<id>"
    resolve_match = re.match(r"^(?:resolver|resolve)\s+#?(.+)$", msg)
    if resolve_match:
        arg = message.strip().split(None, 1)[1].lstrip("#").strip() if len(message.strip().split(None, 1)) > 1 else resolve_match.group(1).strip()
        return Intent.RESOLVE_NOTIFICATION, arg

    # Mark read: "leido", "leidos", "mark read"
    if msg in ("leido", "leidos", "mark read"):
        return Intent.MARK_READ_NOTIFICATIONS, None

    # Approve draft: "aprobar #<id>" or "approve #<id>"
    approve_match = re.match(r"^(?:aprobar|approve)\s+#?(.+)$", msg)
    if approve_match:
        arg = message.strip().split(None, 1)[1].lstrip("#").strip() if len(message.strip().split(None, 1)) > 1 else approve_match.group(1).strip()
        return Intent.APPROVE_DRAFT, arg

    # Reject draft: "rechazar #<id>" or "reject #<id>"
    reject_match = re.match(r"^(?:rechazar|reject)\s+#?(.+)$", msg)
    if reject_match:
        arg = message.strip().split(None, 1)[1].lstrip("#").strip() if len(message.strip().split(None, 1)) > 1 else reject_match.group(1).strip()
        return Intent.REJECT_DRAFT, arg

    # Generate draft: "generar draft <lead_name>" or "draft para <lead_name>"
    gen_match = re.match(r"^generar\s+draft\s+(.+)$", msg)
    if gen_match:
        orig_arg = message.strip()[len("generar draft"):].strip()
        return Intent.GENERATE_DRAFT, orig_arg

    draft_para_match = re.match(r"^draft\s+para\s+(.+)$", msg)
    if draft_para_match:
        orig_arg = message.strip()[len("draft para"):].strip()
        return Intent.GENERATE_DRAFT, orig_arg

    # -- Read-only intents (Etapa 2) --

    # Lead detail: "lead <name or id>"
    lead_detail_match = re.match(r"^lead\s+(.+)$", msg)
    if lead_detail_match:
        # Extract arg from original message to preserve case
        orig_arg = message.strip()[len('lead'):].strip()
        return Intent.QUERY_LEAD_DETAIL, orig_arg

    # Notifications
    if msg in ("notificaciones", "alertas", "notifications"):
        return Intent.QUERY_NOTIFICATIONS, None

    # Drafts
    if msg in ("borradores", "drafts"):
        return Intent.QUERY_DRAFTS, None

    # Stats — exact keywords and natural-language patterns
    if msg in ("stats", "estadisticas", "resumen", "estad\u00edsticas"):
        return Intent.QUERY_STATS, None
    if re.search(r"cuantos?\s+leads", msg) or re.search(r"cuántos?\s+leads", msg):
        return Intent.QUERY_STATS, None
    if re.search(r"(resumen|overview|metricas|métricas|numeros|números|dashboard)", msg):
        return Intent.QUERY_STATS, None

    # Leads (generic) — exact keywords and natural-language patterns
    if msg in ("leads", "prospectos"):
        return Intent.QUERY_LEADS, None
    if re.search(r"(mejores|top|mejores?\s+leads|top\s+leads|listado?\s+de?\s+leads)", msg):
        return Intent.QUERY_LEADS, None

    # Notifications — natural-language patterns
    if re.search(r"(alertas?|notificacion|hay\s+alertas|hay\s+notificacion)", msg):
        return Intent.QUERY_NOTIFICATIONS, None

    # Drafts — natural-language patterns
    if re.search(r"(borrador|draft|pendientes?\s+de\s+revision)", msg):
        return Intent.QUERY_DRAFTS, None

    return Intent.HELP, None


# -- Query implementations --


def _query_leads(db: Session) -> str:
    """Top 5 leads by score."""
    stmt = (
        select(Lead)
        .where(Lead.score.isnot(None))
        .order_by(Lead.score.desc())
        .limit(5)
    )
    leads = db.execute(stmt).scalars().all()
    if not leads:
        return "No hay leads con score asignado todavia."

    lines = ["*Top 5 Leads por Score:*", ""]
    for i, lead in enumerate(leads, 1):
        status = lead.status.value if hasattr(lead.status, "value") else lead.status
        lines.append(
            f"{i}. *{lead.business_name}* \u2014 Score: {lead.score:.0f}, Estado: {status}"
        )
    return "\n".join(lines)


def _query_lead_detail(db: Session, search: str) -> str:
    """Find lead by name (ilike) or UUID."""
    lead = None

    # Try UUID first
    try:
        uid = uuid.UUID(search)
        lead = db.get(Lead, uid)
    except (ValueError, AttributeError):
        pass

    # Fallback to name search
    if lead is None:
        stmt = select(Lead).where(Lead.business_name.ilike(f"%{search}%")).limit(1)
        lead = db.execute(stmt).scalars().first()

    if not lead:
        return f"No se encontro ningun lead con: _{search}_"

    status = lead.status.value if hasattr(lead.status, "value") else lead.status
    score_str = f"{lead.score:.0f}" if lead.score is not None else "sin score"

    lines = [
        f"*{lead.business_name}*",
        f"Score: {score_str}",
        f"Estado: {status}",
        f"Ciudad: {lead.city or 'N/A'}",
        f"Web: {lead.website_url or 'N/A'}",
        f"Email: {lead.email or 'N/A'}",
    ]
    return "\n".join(lines)


def _query_notifications(db: Session) -> str:
    """Last 5 unread notifications."""
    stmt = (
        select(Notification)
        .where(Notification.status == NotificationStatus.UNREAD)
        .order_by(Notification.created_at.desc())
        .limit(5)
    )
    notifs = db.execute(stmt).scalars().all()
    if not notifs:
        return "No hay notificaciones sin leer."

    lines = ["*Ultimas notificaciones sin leer:*", ""]
    for n in notifs:
        sev = n.severity.value if hasattr(n.severity, "value") else n.severity
        msg_preview = n.message[:100]
        lines.append(f"[{sev.upper()}] {n.title} \u2014 {msg_preview}")
    return "\n".join(lines)


def _query_drafts(db: Session) -> str:
    """Last 5 pending drafts."""
    stmt = (
        select(OutreachDraft)
        .where(OutreachDraft.status == DraftStatus.PENDING_REVIEW)
        .order_by(OutreachDraft.generated_at.desc())
        .limit(5)
    )
    drafts = db.execute(stmt).scalars().all()
    if not drafts:
        return "No hay borradores pendientes de revision."

    lines = ["*Borradores pendientes:*", ""]
    for d in drafts:
        # Get recipient name from the lead relationship
        lead_name = d.lead.business_name if d.lead else "Desconocido"
        lines.append(f"*{d.subject}* \u2192 {lead_name}")
    return "\n".join(lines)


def _query_stats(db: Session) -> str:
    """Aggregate lead statistics."""
    total = db.execute(select(func.count(Lead.id))).scalar() or 0
    scored = db.execute(
        select(func.count(Lead.id)).where(Lead.score.isnot(None))
    ).scalar() or 0
    contacted = db.execute(
        select(func.count(Lead.id)).where(
            Lead.status.in_([
                LeadStatus.CONTACTED,
                LeadStatus.OPENED,
                LeadStatus.REPLIED,
                LeadStatus.MEETING,
                LeadStatus.WON,
            ])
        )
    ).scalar() or 0
    replied = db.execute(
        select(func.count(Lead.id)).where(Lead.status == LeadStatus.REPLIED)
    ).scalar() or 0
    avg_score = db.execute(
        select(func.avg(Lead.score)).where(Lead.score.isnot(None))
    ).scalar()
    avg_str = f"{avg_score:.1f}" if avg_score is not None else "N/A"

    lines = [
        "*Resumen de ClawScout:*",
        "",
        f"Total leads: {total}",
        f"Con score: {scored}",
        f"Contactados: {contacted}",
        f"Respondieron: {replied}",
        f"Score promedio: {avg_str}",
    ]
    return "\n".join(lines)


def _help_message(unknown_cmd: str | None = None) -> str:
    """Return available commands in Spanish."""
    lines: list[str] = []
    if unknown_cmd:
        lines.append(f"No entendi el comando: _{unknown_cmd}_")
        lines.append("")
    lines.extend([
        "*Comandos disponibles:*",
        "",
        "*leads* \u2014 Ver los 5 mejores prospectos",
        "*lead <nombre>* \u2014 Detalle de un lead",
        "*notificaciones* \u2014 Ultimas alertas sin leer",
        "*borradores* \u2014 Borradores pendientes",
        "*stats* \u2014 Resumen general",
        "*resolver #<id>* \u2014 Resolver notificacion",
        "*leido* \u2014 Marcar todas las notificaciones como leidas",
        "*aprobar #<id>* \u2014 Aprobar borrador",
        "*rechazar #<id>* \u2014 Rechazar borrador",
        "*generar draft <nombre>* \u2014 Generar borrador para un lead",
        "*ayuda* \u2014 Mostrar este mensaje",
        "",
        "O escribi cualquier pregunta y OpenClaw te responde (si esta activado).",
    ])
    return "\n".join(lines)


def _get_action_description(intent: Intent, extra: str | None) -> str:
    """Return a Spanish description for the pending action confirmation."""
    if intent == Intent.RESOLVE_NOTIFICATION:
        return "Resolver notificacion #" + (extra or "?")
    if intent == Intent.MARK_READ_NOTIFICATIONS:
        return "Marcar todas las notificaciones como leidas"
    if intent == Intent.APPROVE_DRAFT:
        return "Aprobar borrador #" + (extra or "?")
    if intent == Intent.REJECT_DRAFT:
        return "Rechazar borrador #" + (extra or "?")
    if intent == Intent.GENERATE_DRAFT:
        return "Generar draft para " + (extra or "?")
    return "Accion desconocida"


def _get_action_params(intent: Intent, extra: str | None) -> dict:
    """Build params dict for the pending action."""
    if intent == Intent.RESOLVE_NOTIFICATION:
        return {"notification_id": extra or ""}
    if intent == Intent.MARK_READ_NOTIFICATIONS:
        return {}
    if intent == Intent.APPROVE_DRAFT:
        return {"draft_id": extra or ""}
    if intent == Intent.REJECT_DRAFT:
        return {"draft_id": extra or ""}
    if intent == Intent.GENERATE_DRAFT:
        return {"lead_name": extra or ""}
    return {}


def _execute_confirmed_action(db: Session, intent: str, params: dict) -> str:
    """Execute a confirmed action and return the result message."""
    from app.services.whatsapp_actions import (
        execute_approve_draft,
        execute_generate_draft,
        execute_mark_read_all,
        execute_reject_draft,
        execute_resolve_notification,
    )

    if intent == Intent.RESOLVE_NOTIFICATION.value:
        return execute_resolve_notification(db, params.get("notification_id", ""))
    if intent == Intent.MARK_READ_NOTIFICATIONS.value:
        return execute_mark_read_all(db)
    if intent == Intent.APPROVE_DRAFT.value:
        return execute_approve_draft(db, params.get("draft_id", ""))
    if intent == Intent.REJECT_DRAFT.value:
        return execute_reject_draft(db, params.get("draft_id", ""))
    if intent == Intent.GENERATE_DRAFT.value:
        return execute_generate_draft(db, params.get("lead_name", ""))
    return "Accion no reconocida."


def _is_actions_enabled(db: Session) -> bool:
    """Check if WhatsApp actions are enabled in operational settings."""
    from app.models.settings import OperationalSettings
    settings = db.get(OperationalSettings, 1)
    if settings is None:
        return False
    return bool(getattr(settings, "whatsapp_actions_enabled", False))


# -- Main entry point --


def handle_inbound_message(db: Session, phone: str, message: str) -> str:
    """Process an inbound WhatsApp message and return a text response.

    This is the main entry point called by the webhook endpoint.
    Handles both read-only queries and confirmed actions.
    """
    from app.services.whatsapp_confirmation import (
        cancel_pending,
        confirm_pending,
        create_pending,
        has_pending,
        is_locked,
        record_failed_confirmation,
    )
    from app.services.whatsapp_actions import check_action_rate_limit

    # Rate limit check
    if not _check_rate_limit(phone, db):
        logger.warning("wa_rate_limited", phone=phone[:6] + "***")
        return "Has superado el limite de mensajes (20 cada 15 min). Intenta mas tarde."

    # Sanitize input
    clean = _sanitize(message)
    if clean is None:
        logger.warning("wa_suspicious_input", phone=phone[:6] + "***")
        return "Mensaje rechazado por contenido no permitido."

    if not clean:
        return _help_message()

    # Check if phone is locked out from actions
    if is_locked(phone):
        logger.warning("wa_phone_locked_attempt", phone=phone[:6] + "***")
        return "Tu numero esta temporalmente bloqueado por intentos fallidos. Intenta en 15 minutos."

    # Check if there is a pending confirmation for this phone
    if has_pending(phone):
        normalized = clean.lower().strip()
        if normalized in ("si", "SI", "s\u00ed", "sI"):
            # Always check normalized lowercase
            pass
        # Accept SI/si/yes
        if normalized in ("si", "s\u00ed", "yes"):
            action = confirm_pending(phone)
            if action is None:
                return "No hay accion pendiente o ya expiro."
            logger.info(
                "wa_action_confirmed",
                phone=phone[:6] + "***",
                intent=action.intent,
            )
            return _execute_confirmed_action(db, action.intent, action.params)
        # Accept NO/no
        if normalized in ("no",):
            cancelled = cancel_pending(phone)
            if cancelled:
                return "Accion cancelada."
            return "No hay accion pendiente."
        # Anything else while pending is a failed confirmation
        locked = record_failed_confirmation(phone)
        if locked:
            cancel_pending(phone)
            return "Demasiados intentos incorrectos. Numero bloqueado por 15 minutos."
        return "Responde *SI* para confirmar o *NO* para cancelar la accion pendiente."

    # Detect intent
    intent, extra = _detect_intent(clean)
    logger.info("wa_intent_detected", intent=intent.value, phone=phone[:6] + "***")

    # Handle action intents
    if intent in _ACTION_INTENTS:
        # Check if actions are enabled
        if not _is_actions_enabled(db):
            return "Las acciones via WhatsApp no estan habilitadas. Activalas desde Configuracion."

        # Check action rate limit
        if not check_action_rate_limit(phone):
            return "Has superado el limite de acciones (10 por hora). Intenta mas tarde."

        # Create pending confirmation
        description = _get_action_description(intent, extra)
        params = _get_action_params(intent, extra)
        return create_pending(
            phone=phone,
            intent=intent.value,
            params=params,
            description_es=description,
        )

    # Route to read-only handler
    if intent == Intent.QUERY_LEADS:
        return _query_leads(db)
    if intent == Intent.QUERY_LEAD_DETAIL:
        return _query_lead_detail(db, extra or "")
    if intent == Intent.QUERY_NOTIFICATIONS:
        return _query_notifications(db)
    if intent == Intent.QUERY_DRAFTS:
        return _query_drafts(db)
    if intent == Intent.QUERY_STATS:
        return _query_stats(db)

    # HELP — explicit help request
    if intent == Intent.HELP and clean.lower() in ("help", "ayuda", "?", "comandos"):
        return _help_message()

    # OpenClaw chat fallback — route unknown messages to AI
    from app.models.settings import OperationalSettings
    ops = db.get(OperationalSettings, 1)
    if ops and getattr(ops, "whatsapp_openclaw_enrichment", False):
        from app.services.openclaw_chat_service import chat_with_openclaw
        logger.info("wa_routing_to_openclaw", phone=phone[:6] + "***")
        return chat_with_openclaw(db, phone, clean)

    # Final fallback — show help with unknown command hint
    return _help_message(clean)
