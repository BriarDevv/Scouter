"""Scout agent tools — synchronous Playwright-based investigation tools.

These tools run inside a Celery worker (not async). They use Playwright
sync API when available, falling back to httpx for basic HTTP fetching.

Each tool returns a dict result that gets formatted as a tool_response
for the Scout agent loop.
"""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}")
_WHATSAPP_RE = re.compile(r"wa\.me|whatsapp\.com|api\.whatsapp", re.IGNORECASE)
_BOOKING_RE = re.compile(
    r"booksy|calendly|reservar|turnero|appointy|setmore|acuityscheduling",
    re.IGNORECASE,
)
_JUNK_EMAIL_DOMAINS = {
    "example.com",
    "sentry.io",
    "wixpress.com",
    "w3.org",
    "schema.org",
    "googleapis.com",
}

# Max text we extract from a page to stay within token budget
_MAX_PAGE_TEXT = 3000
_HTTP_TIMEOUT = 15

# SSRF protection — block private IPs and dangerous schemes
_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "data", "javascript"}


def _validate_url(url: str) -> str | None:
    """Validate URL is safe for external fetching. Returns None if blocked (SSRF protection).

    Resolves the hostname and pins the first safe IP to prevent DNS rebinding
    (TOCTOU between validation and fetch).
    """
    import ipaddress
    import socket
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(url)
    if parsed.scheme.lower() in _BLOCKED_SCHEMES:
        return None
    hostname = parsed.hostname
    if not hostname:
        return None

    def _is_safe_ip(ip_str: str) -> bool:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)

    # Check if hostname is a direct IP
    try:
        ipaddress.ip_address(hostname)
        if not _is_safe_ip(hostname):
            return None
        return url
    except ValueError:
        pass

    # Hostname is a domain — resolve, check all IPs, pin the first safe one
    try:
        resolved = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        return None

    for _, _, _, _, addr in resolved:
        if not _is_safe_ip(addr[0]):
            return None

    # Pin resolved IP into URL to prevent DNS rebinding
    if resolved:
        pinned_ip = resolved[0][4][0]
        pinned = parsed._replace(
            netloc=f"{pinned_ip}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"
        )
        return urlunparse(pinned)
    return None


def _is_junk_email(email: str) -> bool:
    domain = email.split("@")[-1].lower()
    return domain in _JUNK_EMAIL_DOMAINS or email.startswith("noreply")


def _get_page_httpx(url: str) -> dict:
    """Fetch a page with httpx (fallback when Playwright not available)."""
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            start = time.monotonic()
            resp = client.get(url, headers={"User-Agent": "Scouter-Scout/1.0 (research)"})
            elapsed_ms = int((time.monotonic() - start) * 1000)
            text = resp.text[:50_000]
            return {
                "url": str(resp.url),
                "status_code": resp.status_code,
                "elapsed_ms": elapsed_ms,
                "html": text,
                "error": None,
            }
    except Exception as exc:
        return {"url": url, "status_code": 0, "elapsed_ms": 0, "html": "", "error": str(exc)}


def _try_playwright(url: str) -> dict | None:
    """Try to use Playwright sync API. Returns None if not installed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            start = time.monotonic()
            page.goto(url, timeout=_HTTP_TIMEOUT * 1000, wait_until="domcontentloaded")
            elapsed_ms = int((time.monotonic() - start) * 1000)
            html = page.content()[:50_000]
            title = page.title()
            final_url = page.url
            browser.close()
            return {
                "url": final_url,
                "status_code": 200,
                "elapsed_ms": elapsed_ms,
                "html": html,
                "title": title,
                "error": None,
            }
    except Exception as exc:
        return {"url": url, "status_code": 0, "elapsed_ms": 0, "html": "", "error": str(exc)}


def _extract_text_from_html(html: str) -> str:
    """Extract visible text from HTML, stripping tags."""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:_MAX_PAGE_TEXT]
    except Exception:
        clean = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", clean).strip()[:_MAX_PAGE_TEXT]


# ---------------------------------------------------------------------------
# Public tool functions — called by Scout agent loop
# ---------------------------------------------------------------------------


def browse_page(url: str) -> dict[str, Any]:
    """Browse a web page and return its content summary.

    Tries Playwright first (JS rendering), falls back to httpx.
    """
    if not url or url.lower() in ("none", "null", "no proporcionado"):
        return {"error": "No URL provided", "url": url}

    # Ensure URL has protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # SSRF protection — block private IPs and dangerous schemes
    if _validate_url(url) is None:
        return {
            "error": "URL blocked by security policy (private IP or dangerous scheme)",
            "url": url,
        }

    result = _try_playwright(url)
    if result is None:
        result = _get_page_httpx(url)

    html = result.get("html", "")
    text = _extract_text_from_html(html)

    # Extract basic meta
    title = result.get("title", "")
    if not title:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

    meta_desc = ""
    meta_match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.IGNORECASE
    )
    if meta_match:
        meta_desc = meta_match.group(1).strip()

    return {
        "url": result["url"],
        "status_code": result["status_code"],
        "elapsed_ms": result["elapsed_ms"],
        "title": title,
        "meta_description": meta_desc,
        "text_preview": text[:1500],
        "whatsapp_detected": bool(_WHATSAPP_RE.search(html)),
        "booking_system": _BOOKING_RE.search(html).group(0) if _BOOKING_RE.search(html) else None,
        "error": result.get("error"),
    }


def extract_contacts(url: str) -> dict[str, Any]:
    """Extract emails, phones, and WhatsApp links from a page."""
    if not url or url.lower() in ("none", "null"):
        return {"error": "No URL provided", "emails": [], "phones": [], "whatsapp": False}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if _validate_url(url) is None:
        return {
            "error": "URL blocked by security policy",
            "emails": [],
            "phones": [],
            "whatsapp": False,
        }

    result = _try_playwright(url)
    if result is None:
        result = _get_page_httpx(url)

    html = result.get("html", "")

    emails = list({e for e in _EMAIL_RE.findall(html) if not _is_junk_email(e)})
    phones = list(set(_PHONE_RE.findall(html)))[:5]
    whatsapp = bool(_WHATSAPP_RE.search(html))

    return {
        "url": result["url"],
        "emails": emails[:5],
        "phones": phones,
        "whatsapp_detected": whatsapp,
        "error": result.get("error"),
    }


def check_technical(url: str) -> dict[str, Any]:
    """Check technical quality: SSL, mobile-friendliness, load time, basic SEO."""
    if not url or url.lower() in ("none", "null"):
        return {"error": "No URL provided"}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if _validate_url(url) is None:
        return {"error": "URL blocked by security policy"}

    result = _try_playwright(url)
    if result is None:
        result = _get_page_httpx(url)

    html = result.get("html", "")
    has_ssl = result["url"].startswith("https://")
    has_viewport = bool(re.search(r'<meta[^>]*name=["\']viewport', html, re.IGNORECASE))
    has_title = bool(re.search(r"<title[^>]*>.+</title>", html, re.IGNORECASE | re.DOTALL))
    has_meta_desc = bool(re.search(r'<meta[^>]*name=["\']description', html, re.IGNORECASE))
    has_h1 = bool(re.search(r"<h1[^>]*>.+</h1>", html, re.IGNORECASE | re.DOTALL))
    load_ms = result["elapsed_ms"]

    issues = []
    if not has_ssl:
        issues.append("NO_SSL")
    if not has_viewport:
        issues.append("NO_MOBILE_FRIENDLY")
    if load_ms > 3000:
        issues.append("SLOW_LOAD")
    if not has_title or not has_meta_desc:
        issues.append("WEAK_SEO")

    return {
        "url": result["url"],
        "has_ssl": has_ssl,
        "has_viewport_meta": has_viewport,
        "has_title": has_title,
        "has_meta_description": has_meta_desc,
        "has_h1": has_h1,
        "load_time_ms": load_ms,
        "issues": issues,
        "error": result.get("error"),
    }


def take_screenshot(url: str) -> dict[str, Any]:
    """Take a screenshot of a page (requires Playwright)."""
    if not url or url.lower() in ("none", "null"):
        return {"error": "No URL provided"}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if _validate_url(url) is None:
        return {"error": "URL blocked by security policy", "url": url, "screenshot_path": None}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "url": url,
            "screenshot_path": None,
            "error": "Playwright not installed — screenshot unavailable",
        }

    try:
        import os
        from datetime import datetime

        artifacts_dir = os.path.join("storage", "screenshots")
        os.makedirs(artifacts_dir, exist_ok=True)
        filename = f"scout_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(url) % 10000}.png"
        filepath = os.path.join(artifacts_dir, filename)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(url, timeout=_HTTP_TIMEOUT * 1000, wait_until="domcontentloaded")
            page.screenshot(path=filepath)
            browser.close()

        return {"url": url, "screenshot_path": filepath, "error": None}
    except Exception as exc:
        return {"url": url, "screenshot_path": None, "error": str(exc)}


def search_competitors(industry: str, city: str) -> dict[str, Any]:
    """Search for competitors in the same industry and city.

    Uses a simple Google search via httpx (no API key needed).
    Returns top results as basic summaries.
    """
    query = f"{industry} {city} sitio web"
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(
                "https://www.google.com/search",
                params={"q": query, "num": 5, "hl": "es"},
                headers={"User-Agent": "Mozilla/5.0 (compatible; Scouter-Scout/1.0)"},
            )
            # Extract basic result titles/URLs from HTML
            results = []
            for match in re.finditer(
                r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                resp.text,
            ):
                url, title = match.group(1), re.sub(r"<[^>]+>", "", match.group(2))
                if "google.com" not in url and title.strip():
                    results.append({"url": url, "title": title.strip()[:100]})
                    if len(results) >= 5:
                        break
            return {"query": query, "results": results, "error": None}
    except Exception as exc:
        return {"query": query, "results": [], "error": str(exc)}


def finish_investigation(findings: str) -> dict[str, Any]:
    """Signal that the investigation is complete and return findings.

    The findings parameter should be a JSON string with the investigation summary.
    """
    import json

    try:
        parsed = json.loads(findings) if isinstance(findings, str) else findings
        return {"status": "completed", "findings": parsed}
    except (json.JSONDecodeError, TypeError):
        return {"status": "completed", "findings": {"raw": findings}}


# ---------------------------------------------------------------------------
# Tool registry for Scout (separate from Mote's registry)
# ---------------------------------------------------------------------------

SCOUT_TOOLS: dict[str, dict] = {
    "browse_page": {
        "handler": browse_page,
        "description": (
            "Browse a web page and get its content, title, meta, WhatsApp detection,"
            " and booking system detection."
        ),
        "parameters": [
            {"name": "url", "type": "string", "description": "URL to browse", "required": True}
        ],
    },
    "extract_contacts": {
        "handler": extract_contacts,
        "description": "Extract emails, phones, and WhatsApp links from a web page.",
        "parameters": [
            {
                "name": "url",
                "type": "string",
                "description": "URL to extract contacts from",
                "required": True,
            }
        ],
    },
    "check_technical": {
        "handler": check_technical,
        "description": "Check technical quality of a website: SSL, mobile, speed, SEO basics.",
        "parameters": [
            {"name": "url", "type": "string", "description": "URL to check", "required": True}
        ],
    },
    "take_screenshot": {
        "handler": take_screenshot,
        "description": "Take a screenshot of a web page (requires Playwright).",
        "parameters": [
            {"name": "url", "type": "string", "description": "URL to screenshot", "required": True}
        ],
    },
    "search_competitors": {
        "handler": search_competitors,
        "description": "Search for competitors in the same industry and city.",
        "parameters": [
            {
                "name": "industry",
                "type": "string",
                "description": "Industry/business type",
                "required": True,
            },
            {
                "name": "city",
                "type": "string",
                "description": "City to search in",
                "required": True,
            },
        ],
    },
    "finish_investigation": {
        "handler": finish_investigation,
        "description": "Complete the investigation and return your findings as a JSON summary.",
        "parameters": [
            {
                "name": "findings",
                "type": "string",
                "description": "JSON string with investigation findings",
                "required": True,
            }
        ],
    },
}


def build_scout_tools_schema() -> str:
    """Build Hermes 3 compatible tool schema for Scout's toolset."""
    import json

    tools_xml = []
    for name, tool in SCOUT_TOOLS.items():
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        p["name"]: {"type": p["type"], "description": p["description"]}
                        for p in tool["parameters"]
                    },
                    "required": [p["name"] for p in tool["parameters"] if p.get("required")],
                },
            },
        }
        tools_xml.append(f"<tool>\n{json.dumps(schema, ensure_ascii=False)}\n</tool>")
    return "\n".join(tools_xml)
