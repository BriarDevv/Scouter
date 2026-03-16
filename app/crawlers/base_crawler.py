"""Base crawler interface and example implementation.

All crawlers must implement the BaseCrawler interface.
Crawlers are responsible for discovering leads from public sources.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RawLead:
    """Raw lead data extracted by a crawler before normalization."""

    business_name: str
    industry: str | None = None
    city: str | None = None
    zone: str | None = None
    website_url: str | None = None
    instagram_url: str | None = None
    email: str | None = None
    phone: str | None = None
    source_url: str | None = None
    # Extended fields from Google Maps
    address: str | None = None
    google_maps_url: str | None = None
    rating: float | None = None
    review_count: int | None = None
    business_status: str | None = None
    opening_hours: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class BaseCrawler(ABC):
    """Abstract base class for all crawlers."""

    def __init__(self) -> None:
        self.rate_limit = settings.CRAWLER_RATE_LIMIT_PER_SECOND
        self._last_request_time: float = 0

    def _throttle(self) -> None:
        """Enforce rate limiting between requests."""
        if self.rate_limit <= 0:
            return
        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()

    def _fetch(self, url: str) -> httpx.Response:
        """Fetch a URL with rate limiting and proper headers."""
        self._throttle()
        with httpx.Client(
            timeout=settings.CRAWLER_TIMEOUT,
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            follow_redirects=True,
        ) as client:
            return client.get(url)

    @abstractmethod
    def crawl(self, **kwargs) -> list[RawLead]:
        """Execute the crawl and return discovered leads."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name for this crawler's source."""
        ...


class ExampleDirectoryCrawler(BaseCrawler):
    """Example crawler for a hypothetical public business directory.

    This is a template showing how to implement a crawler.
    Replace the URL and parsing logic with a real public directory.
    """

    @property
    def source_name(self) -> str:
        return "example_directory"

    def crawl(self, url: str, max_pages: int = 5) -> list[RawLead]:
        leads: list[RawLead] = []

        for page in range(1, max_pages + 1):
            page_url = f"{url}?page={page}"
            logger.info("crawling_page", url=page_url, page=page)

            try:
                resp = self._fetch(page_url)
                if resp.status_code != 200:
                    logger.warning("page_fetch_failed", url=page_url, status=resp.status_code)
                    break

                soup = BeautifulSoup(resp.text, "lxml")
                page_leads = self._parse_page(soup, page_url)
                leads.extend(page_leads)

                if not page_leads:
                    break  # No more results

            except Exception as e:
                logger.error("crawl_error", url=page_url, error=str(e))
                break

        logger.info("crawl_completed", source=self.source_name, leads_found=len(leads))
        return leads

    def _parse_page(self, soup: BeautifulSoup, source_url: str) -> list[RawLead]:
        """Parse a directory page. Override this for real directories."""
        leads: list[RawLead] = []

        # Example: parse listing cards (adapt selectors to real directory)
        for card in soup.select(".business-card, .listing-item, article.business"):
            name_el = card.select_one("h2, h3, .business-name")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            if not name:
                continue

            lead = RawLead(
                business_name=name,
                source_url=source_url,
            )

            # Try to extract other fields
            website_el = card.select_one("a[href*='http']")
            if website_el:
                lead.website_url = website_el.get("href")

            phone_el = card.select_one(".phone, [href^='tel:']")
            if phone_el:
                lead.phone = phone_el.get_text(strip=True)

            category_el = card.select_one(".category, .industry")
            if category_el:
                lead.industry = category_el.get_text(strip=True)

            location_el = card.select_one(".location, .city, .address")
            if location_el:
                lead.city = location_el.get_text(strip=True)

            leads.append(lead)

        return leads
