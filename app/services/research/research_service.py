"""Lead research service -- investigates a lead's digital presence."""

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lead import Lead
from app.models.research_report import ConfidenceLevel, LeadResearchReport, ResearchStatus

logger = get_logger(__name__)


def create_or_get_report(db: Session, lead_id: uuid.UUID) -> LeadResearchReport:
    """Get existing report or create a new one (race-safe)."""
    report = db.query(LeadResearchReport).filter_by(lead_id=lead_id).first()
    if not report:
        try:
            report = LeadResearchReport(lead_id=lead_id, status=ResearchStatus.PENDING)
            db.add(report)
            db.flush()
            db.refresh(report)
        except Exception:
            db.rollback()
            report = db.query(LeadResearchReport).filter_by(lead_id=lead_id).first()
            if not report:
                raise
    return report


def run_research(db: Session, lead_id: uuid.UUID) -> LeadResearchReport | None:
    """Run research on a lead -- analyze website, detect signals, build report."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    report = create_or_get_report(db, lead_id)

    # Idempotency: skip if already completed
    if report.status == ResearchStatus.COMPLETED:
        logger.info("research_skipped_already_completed", lead_id=str(lead_id))
        return report

    report.status = ResearchStatus.RUNNING
    db.flush()

    start = time.monotonic()
    try:
        signals: list[dict] = []
        html_meta: dict = {}

        # Website analysis
        if lead.website_url:
            report.website_exists = True
            report.website_url_verified = lead.website_url
            report.website_confidence = ConfidenceLevel.CONFIRMED
            try:
                import httpx

                with httpx.Client(timeout=15, follow_redirects=True) as client:
                    resp = client.get(lead.website_url)
                    if resp.status_code < 400:
                        from bs4 import BeautifulSoup

                        soup = BeautifulSoup(resp.text[:50000], "lxml")
                        html_meta["title"] = (
                            soup.title.string.strip() if soup.title and soup.title.string else None
                        )
                        meta_desc = soup.find("meta", attrs={"name": "description"})
                        html_meta["description"] = (
                            meta_desc["content"] if meta_desc and meta_desc.get("content") else None
                        )
                        og_tags = {}
                        for tag in soup.find_all(
                            "meta",
                            attrs={"property": lambda x: x and x.startswith("og:")},
                        ):
                            og_tags[tag["property"]] = tag.get("content", "")
                        if og_tags:
                            html_meta["og_tags"] = og_tags

                        # Detect WhatsApp
                        page_text = resp.text.lower()
                        if (
                            "wa.me" in page_text
                            or "whatsapp" in page_text
                            or "api.whatsapp.com" in page_text
                        ):
                            report.whatsapp_detected = True
                            report.whatsapp_confidence = ConfidenceLevel.PROBABLE
                            signals.append(
                                {
                                    "type": "whatsapp_detected",
                                    "detail": "WhatsApp link/reference found on website",
                                    "confidence": 0.7,
                                }
                            )
                        else:
                            report.whatsapp_detected = False
                            report.whatsapp_confidence = ConfidenceLevel.UNKNOWN

                        # Check SSL
                        is_https = lead.website_url.startswith("https")
                        if is_https:
                            signals.append(
                                {
                                    "type": "has_ssl",
                                    "detail": "HTTPS detected",
                                    "confidence": 1.0,
                                }
                            )
                    else:
                        report.website_confidence = ConfidenceLevel.MISMATCH
                        signals.append(
                            {
                                "type": "website_error",
                                "detail": f"HTTP {resp.status_code}",
                                "confidence": 0.9,
                            }
                        )
            except Exception as exc:
                report.website_confidence = ConfidenceLevel.MISMATCH
                signals.append(
                    {
                        "type": "website_error",
                        "detail": str(exc)[:200],
                        "confidence": 0.8,
                    }
                )
        else:
            report.website_exists = False
            report.website_confidence = ConfidenceLevel.CONFIRMED
            signals.append(
                {
                    "type": "no_website",
                    "detail": "No website URL in lead data",
                    "confidence": 1.0,
                }
            )

        # Instagram analysis
        if lead.instagram_url:
            report.instagram_exists = True
            report.instagram_url_verified = lead.instagram_url
            report.instagram_confidence = ConfidenceLevel.PROBABLE
        else:
            report.instagram_exists = False
            report.instagram_confidence = ConfidenceLevel.UNKNOWN

        # WhatsApp verification: check Instagram page for wa.me links
        if not report.whatsapp_detected and lead.instagram_url:
            try:
                import httpx as _httpx

                with _httpx.Client(timeout=10, follow_redirects=True) as _client:
                    ig_resp = _client.get(
                        lead.instagram_url,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; Scouter/1.0)"},
                    )
                    if ig_resp.status_code < 400:
                        ig_text = ig_resp.text[:100000].lower()
                        if (
                            "wa.me" in ig_text
                            or "api.whatsapp.com" in ig_text
                            or "whatsapp" in ig_text
                        ):
                            report.whatsapp_detected = True
                            report.whatsapp_confidence = ConfidenceLevel.CONFIRMED
                            signals.append(
                                {
                                    "type": "whatsapp_confirmed",
                                    "detail": "WhatsApp link/mention found on Instagram page",
                                    "confidence": 1.0,
                                }
                            )
            except Exception:  # noqa: S110 — non-critical: fall through to phone heuristic
                pass

        # WhatsApp heuristic: if lead has phone and WhatsApp not yet confirmed,
        # mark as probable (in Argentina ~90%+ businesses with phone have WhatsApp)
        if not report.whatsapp_detected and lead.phone:
            report.whatsapp_detected = True
            report.whatsapp_confidence = ConfidenceLevel.PROBABLE
            signals.append(
                {
                    "type": "whatsapp_probable",
                    "detail": f"Phone detected ({lead.phone[:6]}...) — WhatsApp probable",
                    "confidence": 0.8,
                }
            )

        report.detected_signals_json = signals
        report.html_metadata_json = html_meta if html_meta else None
        report.research_duration_ms = int((time.monotonic() - start) * 1000)
        report.status = ResearchStatus.COMPLETED
        report.updated_at = datetime.now(UTC)
        db.flush()
        db.refresh(report)

        logger.info(
            "research_completed",
            lead_id=str(lead_id),
            signals=len(signals),
            duration_ms=report.research_duration_ms,
        )
        return report

    except Exception as exc:
        report.status = ResearchStatus.FAILED
        report.error = str(exc)[:500]
        report.research_duration_ms = int((time.monotonic() - start) * 1000)
        db.flush()
        logger.error("research_failed", lead_id=str(lead_id), error=str(exc))
        return report
