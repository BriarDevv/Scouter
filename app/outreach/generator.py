"""Outreach draft generation using LLM with post-generation validation."""

import re

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.llm.client import generate_outreach_draft as llm_generate
from app.llm.roles import LLMRole
from app.models.lead import Lead
from app.services.settings.operational_settings_service import get_brand_context

logger = get_logger(__name__)

WORD_LIMIT = 150
PLURAL_MARKERS = ("nosotros", "nuestro", "nuestros", "nuestra", "nuestras", "nuestro equipo")
_URL_RE = re.compile(r"https?://[^\s,)>\]]+", re.IGNORECASE)


def _collect_allowed_urls(lead: Lead, brand_ctx: dict | None) -> set[str]:
    """Build set of known URLs from lead data and brand settings."""
    urls: set[str] = set()
    for val in (
        getattr(lead, "website_url", None),
        getattr(lead, "instagram_url", None),
        (brand_ctx or {}).get("portfolio_url"),
        (brand_ctx or {}).get("website_url"),
        (brand_ctx or {}).get("calendar_url"),
    ):
        if val:
            urls.add(val.rstrip("/"))
    return urls


def _validate_draft(subject: str, body: str, *, brand_ctx: dict | None, lead: Lead) -> tuple[str, str, list[str]]:
    """Validate LLM output against rules. Returns (subject, body, warnings)."""
    warnings: list[str] = []
    bc = brand_ctx or {}

    # 1. Word count
    word_count = len(body.split())
    if word_count > WORD_LIMIT:
        warnings.append(f"body_word_count={word_count} (limit {WORD_LIMIT})")

    # 2. URL fabrication detection
    allowed = _collect_allowed_urls(lead, brand_ctx)
    found_urls = _URL_RE.findall(body)
    for url in found_urls:
        clean = url.rstrip("/.,;:!?")
        if not any(clean.startswith(a) for a in allowed):
            body = body.replace(url, "")
            warnings.append(f"fabricated_url_removed={url}")

    body_lower = body.lower()

    # 3. Solo/plural language check
    if bc.get("signature_is_solo", False):
        for marker in PLURAL_MARKERS:
            if marker in body_lower:
                warnings.append(f"plural_marker_in_solo_draft={marker}")
                break

    # 4. Brand/company name leak detection
    for name_key in ("brand_name", "signature_company"):
        name_val = bc.get(name_key, "")
        if name_val and len(name_val) > 2 and name_val.lower() in body_lower:
            body = re.sub(re.escape(name_val), "", body, flags=re.IGNORECASE)
            body_lower = body.lower()
            warnings.append(f"company_name_removed={name_val}")

    return subject, body, warnings


def _get_brief_angle(lead: Lead, db: Session | None) -> str | None:
    """Return recommended angle from a CommercialBrief, if one exists."""
    if db is None:
        return None
    try:
        from app.models.commercial_brief import CommercialBrief

        brief = db.query(CommercialBrief).filter_by(lead_id=lead.id).first()
        if brief and brief.recommended_angle:
            parts = [brief.recommended_angle]
            if brief.why_this_lead_matters:
                parts.append(brief.why_this_lead_matters)
            return " | ".join(parts)
    except Exception:
        logger.debug("brief_angle_lookup_failed", lead_id=str(lead.id))
    return None


def generate_draft_content(
    lead: Lead,
    db: Session | None = None,
    pipeline_context_text: str = "",
) -> tuple[str, str]:
    """Generate subject and body for an outreach email. Returns (subject, body).

    Args:
        pipeline_context_text: Pre-formatted text from upstream pipeline steps
            (analysis reasoning, research findings, brief assessment, reviewer corrections).
            Injected into the LLM prompt so drafts are informed by the full pipeline.
    """
    brand_ctx = get_brand_context(db) if db is not None else None

    # Enrich suggested angle with CommercialBrief context if available
    suggested_angle = lead.llm_suggested_angle
    brief_angle = _get_brief_angle(lead, db)
    if brief_angle:
        suggested_angle = brief_angle

    result = llm_generate(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        llm_summary=lead.llm_summary,
        llm_suggested_angle=suggested_angle,
        signals=list(lead.signals),
        role=LLMRole.EXECUTOR,
        brand_context=brand_ctx,
        pipeline_context=pipeline_context_text,
    )

    subject, body, warnings = _validate_draft(
        result["subject"], result["body"],
        brand_ctx=brand_ctx, lead=lead,
    )

    if warnings:
        logger.warning("draft_validation_warnings", lead_id=str(lead.id), warnings=warnings)

    return subject, body


WA_WORD_LIMIT = 80
WA_CHAR_LIMIT = 300


def generate_whatsapp_draft_content(lead: Lead, db: Session | None = None) -> str:
    """Generate WhatsApp message body via EXECUTOR model. Returns body string."""
    from app.llm.client import generate_whatsapp_draft as llm_wa_generate

    brand_ctx = get_brand_context(db) if db is not None else None
    result = llm_wa_generate(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        llm_summary=lead.llm_summary,
        llm_suggested_angle=lead.llm_suggested_angle,
        signals=list(lead.signals),
    )

    body = result["body"]
    warnings: list[str] = []

    if len(body.split()) > WA_WORD_LIMIT:
        warnings.append(f"wa_body_words={len(body.split())} (limit {WA_WORD_LIMIT})")

    if len(body) > WA_CHAR_LIMIT:
        body = body[:WA_CHAR_LIMIT - 3] + "..."
        warnings.append(f"wa_body_truncated_at={WA_CHAR_LIMIT}")

    allowed = _collect_allowed_urls(lead, brand_ctx)
    for url in _URL_RE.findall(body):
        clean = url.rstrip("/.,;:!?")
        if not any(clean.startswith(a) for a in allowed):
            body = body.replace(url, "")
            warnings.append(f"fabricated_url_removed={url}")

    if warnings:
        logger.warning("wa_draft_validation_warnings", lead_id=str(lead.id), warnings=warnings)

    return body.strip()
