"""Commercial brief service — generates business intelligence for HIGH leads."""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.commercial_brief import (
    BriefStatus,
    BudgetTier,
    CallDecision,
    CommercialBrief,
    ContactMethod,
    ContactPriority,
    EstimatedScope,
)
from app.models.lead import Lead
from app.models.research_report import LeadResearchReport

logger = get_logger(__name__)

DEFAULT_PRICING_MATRIX = {
    "landing": {"min": 300, "max": 600},
    "institutional_web": {"min": 500, "max": 1200},
    "catalog": {"min": 600, "max": 1500},
    "ecommerce": {"min": 1500, "max": 4000},
    "redesign": {"min": 400, "max": 1000},
    "automation": {"min": 800, "max": 3000},
    "branding_web": {"min": 1000, "max": 2500},
}


def get_pricing_matrix(db: Session) -> dict:
    """Get pricing matrix from settings or default."""
    from app.services.operational_settings_service import get_or_create

    settings = get_or_create(db)
    if settings.pricing_matrix:
        try:
            return json.loads(settings.pricing_matrix)
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULT_PRICING_MATRIX


def create_or_get_brief(
    db: Session, lead_id: uuid.UUID
) -> CommercialBrief:
    """Return existing brief for lead or create a new PENDING one (race-safe)."""
    brief = (
        db.query(CommercialBrief).filter_by(lead_id=lead_id).first()
    )
    if not brief:
        try:
            brief = CommercialBrief(
                lead_id=lead_id, status=BriefStatus.PENDING
            )
            db.add(brief)
            db.commit()
            db.refresh(brief)
        except Exception:
            db.rollback()
            brief = db.query(CommercialBrief).filter_by(
                lead_id=lead_id
            ).first()
            if not brief:
                raise
    return brief


def generate_brief(
    db: Session, lead_id: uuid.UUID
) -> CommercialBrief | None:
    """Generate a commercial brief for a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    brief = create_or_get_brief(db, lead_id)

    # Link research report if exists
    report = (
        db.query(LeadResearchReport).filter_by(lead_id=lead_id).first()
    )
    if report:
        brief.research_report_id = report.id

    try:
        # Get pricing matrix
        pricing = get_pricing_matrix(db)

        # Call LLM to generate brief
        from app.llm.client import generate_commercial_brief_structured
        from app.llm.roles import LLMRole

        llm_result = generate_commercial_brief_structured(
            business_name=lead.business_name,
            industry=lead.industry,
            city=lead.city,
            website_url=lead.website_url,
            instagram_url=lead.instagram_url,
            score=lead.score,
            llm_summary=lead.llm_summary,
            signals=(
                [s.signal_type.value for s in lead.signals]
                if lead.signals
                else []
            ),
            research_data=(
                {
                    "website_confidence": (
                        report.website_confidence.value
                        if report and report.website_confidence
                        else None
                    ),
                    "instagram_confidence": (
                        report.instagram_confidence.value
                        if report and report.instagram_confidence
                        else None
                    ),
                    "whatsapp_detected": (
                        report.whatsapp_detected if report else None
                    ),
                    "html_metadata": (
                        report.html_metadata_json if report else None
                    ),
                    "business_description": (
                        report.business_description if report else None
                    ),
                }
                if report
                else {}
            ),
            pricing_matrix=pricing,
            role=LLMRole.EXECUTOR,
            target_type="commercial_brief",
            target_id=str(brief.id),
            tags={"lead_id": str(lead_id)},
        )
        brief_result = llm_result.parsed

        # Map LLM result to model fields
        brief.opportunity_score = _safe_float(
            brief_result.opportunity_score if brief_result else None, 0, 100
        )

        scope_raw = brief_result.estimated_scope.lower().strip() if brief_result else ""
        brief.estimated_scope = _safe_enum(EstimatedScope, scope_raw)

        # Budget from pricing matrix + scope
        if (
            brief.estimated_scope
            and brief.estimated_scope.value in pricing
        ):
            tier_data = pricing[brief.estimated_scope.value]
            brief.estimated_budget_min = tier_data["min"]
            brief.estimated_budget_max = tier_data["max"]

        brief.budget_tier = _infer_budget_tier(
            brief.estimated_budget_max
        )
        brief.recommended_contact_method = _safe_enum(
            ContactMethod,
            brief_result.recommended_contact_method.lower().strip() if brief_result else "",
        )
        brief.should_call = _safe_enum(
            CallDecision,
            brief_result.should_call.lower().strip() if brief_result else "",
        )
        brief.call_reason = brief_result.call_reason if brief_result else None
        brief.why_this_lead_matters = (
            brief_result.why_this_lead_matters if brief_result else None
        )
        brief.main_business_signals = (
            brief_result.main_business_signals if brief_result else None
        )
        brief.main_digital_gaps = (
            brief_result.main_digital_gaps if brief_result else None
        )
        brief.recommended_angle = (
            brief_result.recommended_angle if brief_result else None
        )
        brief.demo_recommended = brief_result.demo_recommended if brief_result else False
        brief.contact_priority = _infer_contact_priority(
            brief.opportunity_score
        )
        brief.generator_model = llm_result.model
        brief.is_fallback = llm_result.fallback_used
        brief.status = BriefStatus.GENERATED
        brief.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(brief)

        # Emit notification
        try:
            from app.services.notification_emitter import on_brief_generated
            on_brief_generated(
                db,
                lead_id=lead_id,
                business_name=lead.business_name,
                opportunity_score=brief.opportunity_score,
                should_call=(
                    brief.should_call.value if brief.should_call else None
                ),
            )
        except Exception:
            pass

        logger.info(
            "brief_generated",
            lead_id=str(lead_id),
            opportunity_score=brief.opportunity_score,
        )
        return brief

    except Exception as exc:
        brief.status = BriefStatus.FAILED
        brief.error = str(exc)[:500]
        db.commit()
        logger.error(
            "brief_generation_failed",
            lead_id=str(lead_id),
            error=str(exc),
        )
        return brief


def _safe_float(
    val, min_v: float, max_v: float
) -> float | None:
    """Clamp a value to [min_v, max_v], returning None on failure."""
    try:
        v = float(val)
        return max(min_v, min(max_v, v))
    except (TypeError, ValueError):
        return None


def _safe_enum(enum_cls, val: str):
    """Parse an enum value, returning None if invalid."""
    try:
        return enum_cls(val) if val else None
    except ValueError:
        return None


def _infer_budget_tier(max_budget: float | None) -> BudgetTier | None:
    """Derive budget tier from the max budget estimate."""
    if max_budget is None:
        return None
    if max_budget <= 700:
        return BudgetTier.LOW
    if max_budget <= 1500:
        return BudgetTier.MEDIUM
    if max_budget <= 3000:
        return BudgetTier.HIGH
    return BudgetTier.PREMIUM


def _infer_contact_priority(
    opp_score: float | None,
) -> ContactPriority | None:
    """Derive contact priority from the opportunity score."""
    if opp_score is None:
        return None
    if opp_score >= 80:
        return ContactPriority.IMMEDIATE
    if opp_score >= 60:
        return ContactPriority.HIGH
    if opp_score >= 40:
        return ContactPriority.NORMAL
    return ContactPriority.LOW
