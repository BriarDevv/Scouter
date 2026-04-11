"""Notification emitter — emits notifications from business events.

Called from existing services to create structured notifications.
Each function is safe to call (catches all exceptions to avoid breaking the caller).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.notification import NotificationCategory, NotificationSeverity

logger = get_logger(__name__)


def _emit(db: Session, **kwargs) -> None:
    """Safe wrapper around notification creation. Respects notifications_enabled setting."""
    try:
        from app.services.settings.operational_settings_service import get_cached_settings

        ops = get_cached_settings(db)
        if not ops.notifications_enabled:
            return
        from app.services.notifications.notification_service import create_notification

        create_notification(db, **kwargs)
    except Exception as exc:
        logger.error("notification_emit_failed", error=str(exc), type=kwargs.get("type"))


# ---------------------------------------------------------------------------
# Business events
# ---------------------------------------------------------------------------


def on_reply_classified(
    db: Session,
    *,
    message_id: uuid.UUID,
    label: str,
    business_name: str | None,
    from_email: str | None,
    confidence: float | None,
    should_escalate: bool,
) -> None:
    """Emit notification when an inbound reply is classified with an actionable label."""
    high_value_labels = {"interested", "asked_for_quote", "asked_for_meeting"}

    if label not in high_value_labels and not should_escalate:
        return

    label_titles = {
        "interested": "Reply interesada",
        "asked_for_quote": "Pedido de cotizacion",
        "asked_for_meeting": "Pedido de reunion",
    }
    title = label_titles.get(label, f"Reply: {label}")
    if business_name:
        title = f"{title} — {business_name}"

    severity = NotificationSeverity.HIGH
    notif_type = {
        "interested": "reply_interested",
        "asked_for_quote": "quote_request",
        "asked_for_meeting": "meeting_request",
    }.get(label, "reply_important")

    if should_escalate and label not in high_value_labels:
        notif_type = "review_required"
        severity = NotificationSeverity.WARNING
        title = f"Review requerido — {business_name or from_email or 'lead'}"

    _emit(
        db,
        type=notif_type,
        category=NotificationCategory.BUSINESS,
        severity=severity,
        title=title,
        message=(
            f"De: {from_email or 'desconocido'}. Label: {label}. Confianza: {confidence or 0:.0%}."
        ),
        source_kind="inbound_message",
        source_id=message_id,
        metadata={
            "label": label,
            "business_name": business_name,
            "from_email": from_email,
            "confidence": confidence,
        },
        dedup_key=f"reply_classified:{message_id}",
    )


def on_high_score_lead(
    db: Session,
    *,
    lead_id: uuid.UUID,
    business_name: str,
    score: float,
    threshold: float,
) -> None:
    """Emit notification when a lead exceeds the configured score threshold."""
    if score < threshold:
        return

    _emit(
        db,
        type="high_score_lead",
        category=NotificationCategory.BUSINESS,
        severity=NotificationSeverity.WARNING,
        title=f"Lead con score alto — {business_name}",
        message=f"Score: {score:.0f} (umbral: {threshold:.0f}).",
        source_kind="lead",
        source_id=lead_id,
        metadata={"score": score, "business_name": business_name},
        dedup_key=f"high_score:{lead_id}",
    )


def on_draft_needs_review(
    db: Session,
    *,
    draft_id: uuid.UUID,
    business_name: str | None,
    source_type: str = "reply_assistant_draft",
) -> None:
    """Emit notification when a draft requires review before sending."""
    _emit(
        db,
        type="review_required",
        category=NotificationCategory.BUSINESS,
        severity=NotificationSeverity.WARNING,
        title=f"Draft requiere review — {business_name or 'lead'}",
        message="Un draft asistido requiere revision antes de enviar.",
        source_kind=source_type,
        source_id=draft_id,
        metadata={"business_name": business_name},
        dedup_key=f"review_required:{draft_id}",
    )


# ---------------------------------------------------------------------------
# System events
# ---------------------------------------------------------------------------


def on_send_failed(
    db: Session,
    *,
    delivery_id: uuid.UUID | None = None,
    send_id: uuid.UUID | None = None,
    recipient: str | None,
    error: str | None,
    send_type: str = "outreach",
) -> None:
    """Emit notification when an email send fails."""
    source_id = delivery_id or send_id
    _emit(
        db,
        type="send_failed",
        category=NotificationCategory.SYSTEM,
        severity=NotificationSeverity.HIGH,
        title=f"Fallo de envio — {recipient or 'desconocido'}",
        message=f"Tipo: {send_type}. Error: {(error or 'desconocido')[:200]}.",
        source_kind="outreach_delivery" if send_type == "outreach" else "reply_assistant_send",
        source_id=source_id,
        metadata={"recipient": recipient, "error": error, "send_type": send_type},
        dedup_key=f"send_failed:{source_id}" if source_id else None,
    )


def on_sync_failed(
    db: Session,
    *,
    sync_run_id: uuid.UUID | None,
    error: str | None,
) -> None:
    """Emit notification when inbound mail sync fails."""
    _emit(
        db,
        type="sync_failed",
        category=NotificationCategory.SYSTEM,
        severity=NotificationSeverity.HIGH,
        title="Sync de mail entrante fallo",
        message=f"Error: {(error or 'desconocido')[:200]}.",
        source_kind="inbound_mail_sync_run",
        source_id=sync_run_id,
        metadata={"error": error},
        dedup_key=f"sync_failed:{sync_run_id}" if sync_run_id else None,
    )


# ---------------------------------------------------------------------------
# Security events
# ---------------------------------------------------------------------------


def on_security_event(
    db: Session,
    *,
    event_type: str,
    title: str,
    message: str,
    severity: NotificationSeverity | str = NotificationSeverity.HIGH,
    source_kind: str | None = None,
    source_id: uuid.UUID | None = None,
    metadata: dict | None = None,
    dedup_key: str | None = None,
) -> None:
    """Emit a security notification."""
    _emit(
        db,
        type=event_type,
        category=NotificationCategory.SECURITY,
        severity=severity,
        title=title,
        message=message,
        source_kind=source_kind,
        source_id=source_id,
        metadata=metadata,
        dedup_key=dedup_key,
    )


def on_config_insecure(db: Session, *, detail: str) -> None:
    """Emit notification about insecure configuration."""
    _emit(
        db,
        type="config_insecure",
        category=NotificationCategory.SECURITY,
        severity=NotificationSeverity.HIGH,
        title="Configuracion insegura detectada",
        message=detail,
        dedup_key=f"config_insecure:{hash(detail)}",
    )


def on_research_completed(
    db: Session,
    *,
    lead_id: uuid.UUID,
    business_name: str | None,
    signals_count: int,
) -> None:
    """Emit notification when lead research/dossier is completed."""
    _emit(
        db,
        type="research_completed",
        category=NotificationCategory.BUSINESS,
        severity=NotificationSeverity.INFO,
        title=f"Dossier listo — {business_name or 'lead'}",
        message=f"Investigacion completada con {signals_count} senales detectadas.",
        source_kind="lead",
        source_id=lead_id,
        metadata={"business_name": business_name, "signals_count": signals_count},
        dedup_key=f"research_completed:{lead_id}",
    )


def on_brief_generated(
    db: Session,
    *,
    lead_id: uuid.UUID,
    business_name: str | None,
    opportunity_score: float | None,
    should_call: str | None,
) -> None:
    """Emit notification when a commercial brief is generated for a HIGH lead."""
    severity = NotificationSeverity.WARNING
    if should_call == "yes":
        severity = NotificationSeverity.HIGH

    _emit(
        db,
        type="brief_generated",
        category=NotificationCategory.BUSINESS,
        severity=severity,
        title=f"Brief comercial listo — {business_name or 'lead'}",
        message=(
            f"Opportunity score: {opportunity_score or 0:.0f}. "
            f"Llamar: {should_call or 'pendiente'}."
        ),
        source_kind="lead",
        source_id=lead_id,
        metadata={
            "business_name": business_name,
            "opportunity_score": opportunity_score,
            "should_call": should_call,
        },
        dedup_key=f"brief_generated:{lead_id}",
    )


def on_repeated_failures(
    db: Session,
    *,
    failure_type: str,
    count: int,
    detail: str,
) -> None:
    """Emit notification about repeated failures (SMTP, IMAP, etc.)."""
    _emit(
        db,
        type="repeated_failures",
        category=NotificationCategory.SYSTEM,
        severity=NotificationSeverity.HIGH,
        title=f"Fallos repetidos — {failure_type}",
        message=f"{count} fallos recientes. {detail}",
        metadata={"failure_type": failure_type, "count": count},
    )
