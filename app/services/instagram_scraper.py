"""Instagram bio link extractor.

Extracts the external website URL from an Instagram profile's bio.
Uses Playwright to intercept GraphQL responses (bypasses API rate limits).
Falls back to Instagram API if Playwright is unavailable.
"""

import json
import re
import time
from urllib.parse import urlparse

import httpx
from tenacity import retry, retry_if_result, stop_after_attempt, wait_exponential

from app.core.logging import get_logger

logger = get_logger(__name__)

_SOCIAL_DOMAINS = {
    "instagram.com", "facebook.com", "tiktok.com", "twitter.com",
    "x.com", "linkedin.com", "youtube.com", "wa.me", "linktr.ee",
    "bit.ly", "t.me", "linkin.bio", "api.whatsapp.com", "whatsapp.com",
    "maps.app.goo.gl", "maps.google.com", "goo.gl", "drive.google.com",
    "docs.google.com",
}


def _is_real_website(url: str) -> bool:
    """Check if a URL is a real website (not social media or link aggregator)."""
    hostname = urlparse(url).hostname or ""
    return not any(domain in hostname for domain in _SOCIAL_DOMAINS)


def _extract_username(instagram_url: str) -> str | None:
    """Extract username from an Instagram URL."""
    match = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)", instagram_url)
    return match.group(1) if match else None


def _scrape_via_playwright(username: str) -> dict | None:
    """Use Playwright to load the IG profile and intercept the GraphQL response."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    profile_data: dict = {}

    def handle_response(response):
        url = response.url
        if "graphql" in url or "web_profile_info" in url:
            try:
                data = response.json()
                text = json.dumps(data)
                if "external_url" in text or "biography" in text:
                    profile_data["raw"] = data
            except Exception:
                pass

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            page.on("response", handle_response)
            page.goto(
                f"https://www.instagram.com/{username}/",
                wait_until="networkidle",
                timeout=20000,
            )
            page.wait_for_timeout(2000)
            ctx.close()
            browser.close()

        raw = profile_data.get("raw")
        if not raw:
            return None

        user = None
        if "data" in raw and "user" in raw.get("data", {}):
            user = raw["data"]["user"]
        elif "graphql" in raw and "user" in raw.get("graphql", {}):
            user = raw["graphql"]["user"]

        return user
    except Exception as exc:
        logger.warning("ig_playwright_error", username=username, error=str(exc))
        return None


def scrape_instagram_bio_link(instagram_url: str) -> str | None:
    """Extract the website URL from an Instagram profile's bio.

    Returns the website URL if found, None otherwise.
    Uses Playwright GraphQL interception (reliable, no rate limits).
    """
    if not instagram_url:
        return None

    username = _extract_username(instagram_url)
    if not username:
        logger.warning("ig_scrape_bad_url", url=instagram_url)
        return None

    logger.info("ig_scrape_started", username=username)

    # Throttle to be respectful
    time.sleep(2)

    user = _scrape_via_playwright(username)
    if not user:
        logger.info("ig_scrape_no_data", username=username)
        return None

    # Check external_url field
    external_url = user.get("external_url")
    if external_url and _is_real_website(external_url):
        logger.info("ig_scrape_found", username=username, website=external_url)
        return external_url

    # Check bio_links array
    bio_links = user.get("bio_links", [])
    for link in bio_links:
        url = link.get("url", "")
        if url and _is_real_website(url):
            logger.info("ig_scrape_found", username=username, website=url)
            return url

    logger.info("ig_scrape_no_website", username=username,
                external_url=external_url,
                bio_links=[bl.get("url") for bl in bio_links])
    return None
