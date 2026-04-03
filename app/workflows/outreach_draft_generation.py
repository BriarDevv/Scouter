"""Workflow helpers for outreach draft generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.commercial_brief import CommercialBrief
from app.models.lead import Lead
from app.models.outreach import DraftStatus, OutreachDraft
from app.services.operational_settings_service import get_cached_settings
from app.services.outreach_service import generate_outreach_draft, generate_whatsapp_draft

logger = get_logger(__name__)


@dataclass(slots=True)
class OutreachDraftWorkflowResult:
    status: str
    lead_id: str
    draft_id: str | None = None
    reason: str | None = None
    whatsapp_draft_id: str | None = None
    ai_fallback_used: bool = False
    ai_degraded: bool = False

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "lead_id": self.lead_id,
        }
        if self.draft_id:
            payload["draft_id"] = self.draft_id
        if self.reason:
            payload["reason"] = self.reason
        if self.whatsapp_draft_id:
            payload["whatsapp_draft_id"] = self.whatsapp_draft_id
        if self.ai_fallback_used:
            payload["ai_fallback_used"] = True
        if self.ai_degraded:
            payload["ai_degraded"] = True
        return payload


def should_generate_outreach_email_draft(lead: Lead) -> bool:
    """Only generate outreach email drafts for high-quality leads with email."""
    return getattr(lead, "llm_quality", None) == "high" and bool(lead.email)


def run_outreach_draft_generation_workflow(
    db: Session,
    lead_id: uuid.UUID,
) -> OutreachDraftWorkflowResult:
    lead = db.get(Lead, lead_id)
    lead_id_str = str(lead_id)
    if not lead:
        return OutreachDraftWorkflowResult(status="not_found", lead_id=lead_id_str)

    existing_draft = db.execute(
        select(OutreachDraft).where(
            OutreachDraft.lead_id == lead_id,
            OutreachDraft.status.in_(
                [DraftStatus.PENDING_REVIEW, DraftStatus.APPROVED]
            ),
        )
    ).scalar_one_or_none()
    if existing_draft:
        return OutreachDraftWorkflowResult(
            status="skipped",
            lead_id=lead_id_str,
            reason="draft_already_exists",
            draft_id=str(existing_draft.id),
        )

    whatsapp_draft_id: str | None = None
    wa_settings = get_cached_settings(db)

    brief = db.query(CommercialBrief).filter_by(lead_id=lead_id).first()
    if brief and brief.recommended_contact_method:
        method = brief.recommended_contact_method.value
        if method in ("call", "manual_review"):
            return OutreachDraftWorkflowResult(
                status="skipped",
                lead_id=lead_id_str,
                reason=f"contact_method={method}, skipping auto-draft",
            )

        if method == "whatsapp" and lead.phone and wa_settings.whatsapp_outreach_enabled:
            try:
                wa_draft = generate_whatsapp_draft(db, lead_id, commit=False)
                if wa_draft:
                    whatsapp_draft_id = str(wa_draft.id)
                    logger.info(
                        "wa_draft_preferred_by_contact_method",
                        lead_id=lead_id_str,
                        draft_id=whatsapp_draft_id,
                    )
            except Exception as exc:
                logger.warning(
                    "wa_draft_preferred_failed",
                    lead_id=lead_id_str,
                    error=str(exc),
                )

    if not should_generate_outreach_email_draft(lead):
        if whatsapp_draft_id:
            db.commit()
        return OutreachDraftWorkflowResult(
            status="skipped",
            lead_id=lead_id_str,
            reason=f"quality={lead.llm_quality!r}, draft only for high",
            whatsapp_draft_id=whatsapp_draft_id,
        )

    draft = generate_outreach_draft(db, lead_id, commit=False)
    if not draft:
        db.rollback()
        return OutreachDraftWorkflowResult(
            status="failed",
            lead_id=lead_id_str,
            reason="draft_generation_failed",
        )

    if (
        wa_settings.whatsapp_outreach_enabled
        and lead.phone
        and whatsapp_draft_id is None
    ):
        try:
            wa_draft = generate_whatsapp_draft(db, lead_id, commit=False)
            if wa_draft:
                whatsapp_draft_id = str(wa_draft.id)
                logger.info(
                    "wa_draft_generated_by_workflow",
                    lead_id=lead_id_str,
                    draft_id=whatsapp_draft_id,
                )
        except Exception as exc:
            logger.warning(
                "wa_draft_workflow_failed",
                lead_id=lead_id_str,
                error=str(exc),
            )

    db.commit()
    db.refresh(draft)

    generation_metadata = draft.generation_metadata_json or {}
    return OutreachDraftWorkflowResult(
        status="ok",
        lead_id=lead_id_str,
        draft_id=str(draft.id),
        whatsapp_draft_id=whatsapp_draft_id,
        ai_fallback_used=bool(generation_metadata.get("fallback_used")),
        ai_degraded=bool(generation_metadata.get("degraded")),
    )


def run_outreach_draft_automation(db: Session, draft_id: uuid.UUID) -> None:
    """Apply optional auto-approval and auto-send after draft generation."""
    draft = db.get(OutreachDraft, draft_id)
    if not draft:
        return

    ops = get_cached_settings(db)
    if ops.require_approved_drafts or draft.status != DraftStatus.PENDING_REVIEW:
        return

    draft.status = DraftStatus.APPROVED
    draft.reviewed_at = datetime.now(UTC)
    db.commit()
    logger.info("draft_auto_approved", draft_id=str(draft.id), lead_id=str(draft.lead_id))

    if not ops.mail_enabled:
        return

    try:
        from app.services.mail_service import send_draft

        send_draft(db, draft.id)
        logger.info("draft_auto_sent", draft_id=str(draft.id), lead_id=str(draft.lead_id))
    except Exception as exc:
        logger.warning(
            "draft_auto_send_failed",
            draft_id=str(draft.id),
            lead_id=str(draft.lead_id),
            error=str(exc),
        )
