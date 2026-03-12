import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.lead_signal import LeadSignal, SignalType

logger = get_logger(__name__)


@retry(
    stop=stop_after_attempt(settings.CRAWLER_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
def _fetch_url(url: str) -> httpx.Response:
    with httpx.Client(
        timeout=settings.CRAWLER_TIMEOUT,
        headers={"User-Agent": settings.CRAWLER_USER_AGENT},
        follow_redirects=True,
    ) as client:
        return client.get(url)


def _analyze_website(url: str) -> list[tuple[SignalType, str]]:
    """Fetch and analyze a website, returning detected signals."""
    signals: list[tuple[SignalType, str]] = []

    try:
        resp = _fetch_url(url)
    except Exception as e:
        logger.warning("website_fetch_failed", url=url, error=str(e))
        signals.append((SignalType.NO_WEBSITE, f"Could not reach: {e}"))
        return signals

    signals.append((SignalType.HAS_WEBSITE, f"HTTP {resp.status_code}"))

    # SSL check
    parsed = urlparse(url)
    if parsed.scheme != "https":
        signals.append((SignalType.NO_SSL, "Site not served over HTTPS"))

    # Custom domain check
    hostname = parsed.hostname or ""
    free_hosts = ["wixsite.com", "wordpress.com", "blogspot.com", "weebly.com", "carrd.co"]
    if any(fh in hostname for fh in free_hosts):
        signals.append((SignalType.NO_CUSTOM_DOMAIN, f"Hosted on {hostname}"))
    else:
        signals.append((SignalType.HAS_CUSTOM_DOMAIN, hostname))

    # Parse HTML
    soup = BeautifulSoup(resp.text, "lxml")

    # Check viewport meta (mobile-friendly indicator)
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        signals.append((SignalType.NO_MOBILE_FRIENDLY, "No viewport meta tag"))

    # Basic SEO checks
    title = soup.find("title")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if not title or not (title.string or "").strip():
        signals.append((SignalType.WEAK_SEO, "Missing or empty <title>"))
    if not meta_desc:
        signals.append((SignalType.WEAK_SEO, "Missing meta description"))

    # Check for visible email
    text = soup.get_text()
    if "@" not in text and "mailto:" not in resp.text:
        signals.append((SignalType.NO_VISIBLE_EMAIL, "No email found on page"))

    # Outdated indicators
    generator = soup.find("meta", attrs={"name": "generator"})
    if generator:
        content = (generator.get("content") or "").lower()
        if "wordpress" in content:
            # Very rough heuristic: old WP versions
            signals.append((SignalType.OUTDATED_WEBSITE, f"Generator: {content}"))

    return signals


def enrich_lead(db: Session, lead_id: uuid.UUID) -> Lead | None:
    """Run enrichment analysis on a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    logger.info("enrichment_started", lead_id=str(lead_id), business=lead.business_name)

    signals: list[tuple[SignalType, str]] = []

    # Website analysis
    if lead.website_url:
        signals.extend(_analyze_website(lead.website_url))
    else:
        signals.append((SignalType.NO_WEBSITE, "No website URL provided"))

    # Instagram-only check
    if lead.instagram_url and not lead.website_url:
        signals.append((SignalType.INSTAGRAM_ONLY, lead.instagram_url))

    # Store signals (clear old ones first)
    for old_signal in lead.signals:
        db.delete(old_signal)

    for signal_type, detail in signals:
        db.add(LeadSignal(lead_id=lead.id, signal_type=signal_type, detail=detail))

    lead.status = LeadStatus.ENRICHED
    lead.enriched_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lead)

    logger.info(
        "enrichment_completed",
        lead_id=str(lead_id),
        signals_count=len(signals),
    )
    return lead
