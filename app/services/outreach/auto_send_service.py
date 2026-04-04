"""Auto-send service — Mote sends approved drafts automatically in outreach mode.

When runtime_mode is 'outreach', approved drafts are sent by Mote automatically
via the appropriate channel (WhatsApp or email). An OutboundConversation record
tracks the outreach for AI Office visibility.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.outbound_conversation import ConversationStatus, OutboundConversation
from app.models.outreach import DraftStatus, OutreachDraft

logger = structlog.get_logger(__name__)


def auto_send_draft(db: Session, draft_id: uuid.UUID) -> OutboundConversation | None:
    """Auto-send an approved draft and create an OutboundConversation.

    Only sends if:
    - Draft exists and is approved
    - Lead has the required contact info (phone for WhatsApp, email for email)
    - No existing outbound conversation for this draft

    Returns the OutboundConversation record or None if skipped.
    """
    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        logger.warning("auto_send_draft_not_found", draft_id=str(draft_id))
        return None

    if draft.status != DraftStatus.APPROVED:
        logger.debug("auto_send_skip_not_approved", draft_id=str(draft_id), status=draft.status.value)
        return None

    lead = db.get(Lead, draft.lead_id)
    if not lead:
        logger.warning("auto_send_lead_not_found", lead_id=str(draft.lead_id))
        return None

    # Check for existing conversation
    existing = db.query(OutboundConversation).filter_by(draft_id=draft.id).first()
    if existing:
        logger.debug("auto_send_conversation_exists", draft_id=str(draft_id))
        return existing

    channel = getattr(draft, "channel", None) or "email"

    if channel == "whatsapp":
        return _send_whatsapp(db, draft, lead)
    else:
        return _send_email(db, draft, lead)


def _send_whatsapp(db: Session, draft: OutreachDraft, lead: Lead) -> OutboundConversation | None:
    """Send WhatsApp template first, then queue personalized draft for after reply.

    WhatsApp Business API requires a Meta-approved template as the first message
    to a new contact. The personalized draft is stored and sent only after the
    client replies (opening a 24h conversation window).

    Flow:
    1. Select template based on lead signals
    2. Send template via Kapso Cloud API
    3. Store draft in conversation for later delivery
    4. When client replies → closer_service sends the draft
    """
    if not lead.phone:
        logger.warning("auto_send_wa_no_phone", lead_id=str(lead.id))
        return None

    conversation = OutboundConversation(
        lead_id=lead.id,
        draft_id=draft.id,
        channel="whatsapp",
        status=ConversationStatus.DRAFT_READY,
        mode="outreach",
        messages_json=[],
    )
    db.add(conversation)
    db.flush()

    try:
        from app.services.comms.kapso_service import send_template_message
        from app.services.outreach.template_selection import (
            build_template_parameters,
            select_template,
        )

        # Select template based on lead signals
        raw_signals = lead.signals or []
        signals = [s.signal_type.value if hasattr(s, "signal_type") else str(s) for s in raw_signals]
        template = select_template(signals)
        params = build_template_parameters(
            template,
            contact_name=getattr(lead, "contact_name", None) or lead.business_name,
            business_name=lead.business_name,
        )

        # Send template (opens conversation)
        result = send_template_message(
            phone=lead.phone,
            template_name=template.name,
            language=template.language,
            parameters=params,
        )

        conversation.status = ConversationStatus.SENT
        conversation.provider_message_id = result.get("message_id")
        conversation.messages_json = [
            {
                "role": "mote",
                "type": "template",
                "template_name": template.name,
                "timestamp": datetime.now(UTC).isoformat(),
                "provider_message_id": result.get("message_id"),
            },
            {
                "role": "system",
                "type": "queued_draft",
                "content": draft.body,
                "note": "Draft personalizado pendiente — se envía cuando el cliente responde",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        ]

        draft.status = DraftStatus.SENT
        draft.sent_at = datetime.now(UTC)
        db.commit()

        logger.info(
            "auto_send_wa_template_success",
            lead_id=str(lead.id),
            draft_id=str(draft.id),
            conversation_id=str(conversation.id),
            template=template.name,
            phone=lead.phone[:6] + "***",
        )

        # Emit notification
        try:
            from app.services.notifications.notification_emitter import on_outreach_sent
            on_outreach_sent(
                db,
                lead_id=lead.id,
                business_name=lead.business_name,
                channel="whatsapp",
            )
        except Exception:
            logger.debug("outreach_sent_notification_failed", exc_info=True)

        return conversation

    except Exception as exc:
        conversation.status = ConversationStatus.CLOSED
        conversation.error = str(exc)[:500]
        db.commit()
        logger.error(
            "auto_send_wa_failed",
            lead_id=str(lead.id),
            error=str(exc),
        )
        return conversation


def _send_email(db: Session, draft: OutreachDraft, lead: Lead) -> OutboundConversation | None:
    """Send email draft and track the conversation."""
    if not lead.email:
        logger.warning("auto_send_email_no_email", lead_id=str(lead.id))
        return None

    conversation = OutboundConversation(
        lead_id=lead.id,
        draft_id=draft.id,
        channel="email",
        status=ConversationStatus.DRAFT_READY,
        mode="outreach",
        messages_json=[],
    )
    db.add(conversation)
    db.flush()

    try:
        from app.services.outreach.mail_service import send_draft

        send_draft(db, draft.id)
        conversation.status = ConversationStatus.SENT
        conversation.messages_json = [{
            "role": "mote",
            "content": f"Subject: {draft.subject}\n\n{draft.body}",
            "timestamp": datetime.now(UTC).isoformat(),
        }]
        db.commit()

        logger.info(
            "auto_send_email_success",
            lead_id=str(lead.id),
            draft_id=str(draft.id),
        )
        return conversation

    except Exception as exc:
        conversation.status = ConversationStatus.CLOSED
        conversation.error = str(exc)[:500]
        db.commit()
        logger.error("auto_send_email_failed", lead_id=str(lead.id), error=str(exc))
        return conversation


def operator_takeover(db: Session, conversation_id: uuid.UUID) -> OutboundConversation | None:
    """Mark a conversation as taken over by the operator."""
    convo = db.get(OutboundConversation, conversation_id)
    if not convo:
        return None

    convo.operator_took_over = True
    convo.status = ConversationStatus.OPERATOR_TOOK_OVER
    db.commit()

    logger.info("operator_takeover", conversation_id=str(conversation_id), lead_id=str(convo.lead_id))
    return convo
