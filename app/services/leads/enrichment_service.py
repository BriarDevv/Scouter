import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger
from app.models.lead import Lead, LeadStatus
from app.models.lead_signal import LeadSignal, SignalType

logger = get_logger(__name__)


@retry(
    stop=stop_after_attempt(settings.CRAWLER_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)
def _fetch_url(url: str) -> httpx.Response:
    with httpx.Client(
        timeout=settings.CRAWLER_TIMEOUT,
        headers={"User-Agent": settings.CRAWLER_USER_AGENT},
        follow_redirects=True,
    ) as client:
        return client.get(url)


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_JUNK_EMAIL_DOMAINS = {
    "example.com",
    "email.com",
    "test.com",
    "placeholder.com",
    "sentry.io",
    "sentry-next.wixpress.com",
    "wixpress.com",
    "wordpress.com",
    "gravatar.com",
    "w3.org",
    "ingest.de.sentry.io",
    "ingest.sentry.io",
}
_JUNK_EMAIL_PREFIXES = (
    "noreply",
    "no-reply",
    "no_reply",
    "donotreply",
    "notify",
    "notification",
    "alert",
    "mailer-daemon",
    "tuemail",
    "youremail",
    "your-email",
    "tu-email",
)


def _extract_emails(html: str) -> list[str]:
    """Extract real contact emails from HTML, filtering out junk."""
    raw = set(_EMAIL_RE.findall(html))
    emails: list[str] = []
    for email in raw:
        lower = email.lower()
        domain = lower.split("@", 1)[1]
        local = lower.split("@", 1)[0]
        # Skip junk domains
        if domain in _JUNK_EMAIL_DOMAINS or any(jd in domain for jd in ("sentry", "wixpress")):
            continue
        # Skip image-like extensions
        if any(lower.endswith(ext) for ext in (".png", ".jpg", ".svg", ".gif", ".webp")):
            continue
        # Skip placeholder/noreply prefixes
        if any(local.startswith(p) for p in _JUNK_EMAIL_PREFIXES):
            continue
        # Skip hex-like local parts (tracking IDs)
        if len(local) > 20 and all(c in "0123456789abcdef" for c in local.replace("-", "")):
            continue
        emails.append(lower)
    return sorted(set(emails))


def _analyze_website(url: str) -> tuple[list[tuple[SignalType, str]], list[str]]:
    """Fetch and analyze a website, returning detected signals and extracted emails."""
    signals: list[tuple[SignalType, str]] = []
    emails: list[str] = []

    try:
        resp = _fetch_url(url)
    except httpx.TimeoutException as e:
        logger.warning("website_fetch_timeout", url=url, error=str(e))
        signals.append((SignalType.WEBSITE_ERROR, f"Timeout: {e}"))
        return signals, emails
    except httpx.ConnectError as e:
        logger.warning("website_fetch_connect_error", url=url, error=str(e))
        signals.append((SignalType.NO_WEBSITE, f"Could not connect: {e}"))
        return signals, emails
    except Exception as e:
        logger.warning("website_fetch_failed", url=url, error=str(e))
        signals.append((SignalType.WEBSITE_ERROR, f"Error: {e}"))
        return signals, emails

    if resp.status_code >= 500:
        signals.append((SignalType.WEBSITE_ERROR, f"Server error: HTTP {resp.status_code}"))
        return signals, emails

    signals.append((SignalType.HAS_WEBSITE, f"HTTP {resp.status_code}"))

    # Load time check
    if resp.elapsed and resp.elapsed.total_seconds() > 3.0:
        signals.append((SignalType.SLOW_LOAD, f"Load time: {resp.elapsed.total_seconds():.1f}s"))

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

    # Extract emails from page
    emails = _extract_emails(resp.text)

    # If no email on home page, try common subpages
    if not emails:
        base = f"{parsed.scheme}://{parsed.hostname}"
        if parsed.port and parsed.port not in (80, 443):
            base += f":{parsed.port}"
        for subpath in ("/contacto", "/contact", "/about", "/nosotros", "/quienes-somos"):
            try:
                sub_resp = _fetch_url(f"{base}{subpath}")
                if sub_resp.status_code < 400:
                    emails = _extract_emails(sub_resp.text)
                    if emails:
                        logger.info("email_from_subpage", url=url, subpath=subpath, email=emails[0])
                        break
            except Exception:
                continue

    # Check for visible email (signal)
    if not emails:
        signals.append((SignalType.NO_VISIBLE_EMAIL, "No email found on page"))

    # Outdated indicators
    generator = soup.find("meta", attrs={"name": "generator"})
    if generator:
        content = (generator.get("content") or "").lower()
        if "wordpress" in content:
            signals.append((SignalType.OUTDATED_WEBSITE, f"Generator: {content}"))

    return signals, emails


_SOCIAL_MEDIA_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
}


def _is_social_media_url(url: str) -> bool:
    """Check if a URL points to a social media profile, not a real website."""
    hostname = urlparse(url).hostname or ""
    return any(domain in hostname for domain in _SOCIAL_MEDIA_DOMAINS)


def enrich_lead(db: Session, lead_id: uuid.UUID) -> Lead | None:
    """Run enrichment analysis on a lead."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    logger.info("enrichment_started", lead_id=str(lead_id), business=lead.business_name)

    signals: list[tuple[SignalType, str]] = []
    found_emails: list[str] = []

    # If website_url is actually a social media link, move it to the right field
    if lead.website_url and _is_social_media_url(lead.website_url):
        if "instagram.com" in lead.website_url.lower() and not lead.instagram_url:
            lead.instagram_url = lead.website_url
        lead.website_url = None

    # If no website but has Instagram, try to extract website from Instagram bio
    if not lead.website_url and lead.instagram_url:
        try:
            from app.crawlers.instagram_scraper import scrape_instagram_bio_link

            bio_website = scrape_instagram_bio_link(lead.instagram_url)
            if bio_website:
                lead.website_url = bio_website
                logger.info("website_from_instagram", lead_id=str(lead_id), website=bio_website)
        except Exception as exc:
            logger.warning("ig_scrape_skipped", lead_id=str(lead_id), error=str(exc))

    # Website analysis
    if lead.website_url:
        web_signals, found_emails = _analyze_website(lead.website_url)
        signals.extend(web_signals)
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

    # Save extracted email if lead doesn't already have one
    if not lead.email and found_emails:
        lead.email = found_emails[0]
        logger.info("email_extracted", lead_id=str(lead_id), email=found_emails[0])

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
