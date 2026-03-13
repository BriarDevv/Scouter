#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_API_BASE_URL = os.getenv("CLAWSCOUT_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
DEFAULT_TIMEOUT_MS = int(os.getenv("CLAWSCOUT_BROWSER_TIMEOUT_MS", "15000"))
DEFAULT_SCREENSHOT_DIR = os.getenv("CLAWSCOUT_BROWSER_SCREENSHOT_DIR", "/tmp/clawscout-browser")
DEFAULT_IMPORTANT_LINKS_LIMIT = 8
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE_ROOT = SCRIPT_PATH.parent.parent
SOCIAL_PATTERNS = {
    "instagram": ("instagram.com",),
    "facebook": ("facebook.com", "fb.com", "m.facebook.com"),
    "linkedin": ("linkedin.com",),
}
CTA_KEYWORDS = {
    "contact": ("contact", "contacto", "get in touch", "hablanos", "hablemos", "escribinos"),
    "quote": ("quote", "cotiza", "cotizacion", "presupuesto", "pricing"),
    "book": ("book", "reserve", "agendar", "agenda", "schedule", "demo", "meeting"),
    "whatsapp": ("whatsapp",),
}
ECOMMERCE_KEYWORDS = (
    "shop",
    "store",
    "tienda",
    "product",
    "producto",
    "cart",
    "checkout",
    "buy",
    "comprar",
)
CONTACT_LINK_KEYWORDS = ("contact", "contacto", "hablemos", "escribinos", "get in touch")
PHONE_RE = re.compile(r"(?:\+?\d(?:[ .()-]?\d){7,14})")


def ensure_playwright_runtime() -> None:
    if os.environ.get("CLAWSCOUT_BROWSERCTL_REEXEC") == "1":
        return

    try:
        import playwright.sync_api  # noqa: F401
        return
    except ModuleNotFoundError:
        venv_python = WORKSPACE_ROOT / ".venv" / "bin" / "python3"
        if not venv_python.exists():
            return
        env = os.environ.copy()
        env["CLAWSCOUT_BROWSERCTL_REEXEC"] = "1"
        os.execve(
            str(venv_python),
            [str(venv_python), str(SCRIPT_PATH), *sys.argv[1:]],
            env,
        )


ensure_playwright_runtime()

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect public websites with Playwright and return grounded JSON for OpenClaw."
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=DEFAULT_TIMEOUT_MS,
        help=f"Navigation timeout in milliseconds (default: {DEFAULT_TIMEOUT_MS}).",
    )
    parser.add_argument(
        "--screenshot-dir",
        default=DEFAULT_SCREENSHOT_DIR,
        help=f"Directory for screenshots when --screenshot is used (default: {DEFAULT_SCREENSHOT_DIR}).",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help=f"ClawScout API base URL for lead helpers (default: {DEFAULT_API_BASE_URL}).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_url = subparsers.add_parser("inspect-url", help="Inspect a public URL.")
    inspect_url.add_argument("--url", required=True)
    inspect_url.add_argument("--screenshot", action="store_true")
    inspect_url.add_argument("--links-limit", type=int, default=DEFAULT_IMPORTANT_LINKS_LIMIT)

    inspect_business_site = subparsers.add_parser(
        "inspect-business-site",
        help="Fetch a lead from ClawScout and inspect its website_url.",
    )
    inspect_business_site.add_argument("--lead-id", required=True)
    inspect_business_site.add_argument("--screenshot", action="store_true")
    inspect_business_site.add_argument("--links-limit", type=int, default=DEFAULT_IMPORTANT_LINKS_LIMIT)

    return parser.parse_args()


def ok_response(command: str, request_meta: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "request": request_meta,
        "data": data,
    }


def error_response(
    command: str,
    request_meta: dict[str, Any],
    error_type: str,
    message: str,
    *,
    detail: Any | None = None,
) -> dict[str, Any]:
    payload = {
        "ok": False,
        "command": command,
        "request": request_meta,
        "error": {
            "type": error_type,
            "message": message,
        },
    }
    if detail is not None:
        payload["error"]["detail"] = detail
    return payload


def ensure_url(url: str) -> str:
    parsed = parse.urlparse(url)
    if parsed.scheme:
        return url
    return f"https://{url}"


def fetch_lead(api_base_url: str, lead_id: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
    endpoint = f"{api_base_url.rstrip('/')}/leads/{lead_id}"
    req = request.Request(endpoint, headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            detail = raw or None
        raise RuntimeError(f"Lead fetch failed with HTTP {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Lead fetch failed: {exc.reason}") from exc


def collect_page_snapshot(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const anchors = Array.from(document.querySelectorAll('a[href]')).map((el) => ({
                href: el.href,
                text: (el.textContent || '').replace(/\\s+/g, ' ').trim()
            }));
            const forms = Array.from(document.querySelectorAll('form')).map((form) => ({
                hasEmailInput: !!form.querySelector('input[type="email"]'),
                hasPhoneInput: !!form.querySelector('input[type="tel"]'),
                hasTextarea: !!form.querySelector('textarea'),
                submitText: Array.from(form.querySelectorAll('button, input[type="submit"]'))
                    .map((el) => ('value' in el ? el.value : el.textContent || ''))
                    .join(' ')
                    .replace(/\\s+/g, ' ')
                    .trim()
            }));
            const ctaElements = Array.from(document.querySelectorAll('button, a, input[type="submit"]'))
                .map((el) => ('value' in el ? el.value : el.textContent || ''))
                .map((text) => text.replace(/\\s+/g, ' ').trim())
                .filter(Boolean)
                .slice(0, 120);
            return {
                title: document.title || null,
                metaDescription: document.querySelector('meta[name="description"]')?.content || null,
                h1: document.querySelector('h1')?.textContent?.replace(/\\s+/g, ' ').trim() || null,
                visibleText: document.body?.innerText || '',
                anchors,
                forms,
                ctaElements,
            };
        }"""
    )


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def contains_keyword_token(text: str, keyword: str) -> bool:
    return re.search(rf"\b{re.escape(keyword)}s?\b", text, flags=re.IGNORECASE) is not None


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D+", "", raw)
    if len(digits) < 8:
        return None
    return raw.strip()


def extract_contact_signals(text: str, anchors: list[dict[str, str]], forms: list[dict[str, Any]]) -> dict[str, Any]:
    anchor_emails = [
        parse.unquote(anchor["href"].split(":", 1)[1])
        for anchor in anchors
        if anchor["href"].lower().startswith("mailto:")
    ]
    line_email_matches = EMAIL_RE.findall(text)
    email_matches = dedupe_strings(anchor_emails + line_email_matches)

    anchor_phones = [
        parse.unquote(anchor["href"].split(":", 1)[1])
        for anchor in anchors
        if anchor["href"].lower().startswith("tel:")
    ]
    phone_lines = [
        line
        for line in text.splitlines()
        if any(keyword in line.lower() for keyword in ("phone", "tel", "call", "whatsapp", "contact"))
    ]
    line_phone_matches = [
        normalized
        for line in phone_lines
        for raw in PHONE_RE.findall(line)
        if (normalized := normalize_phone(raw))
    ]
    phone_matches = dedupe_strings(anchor_phones + line_phone_matches)
    whatsapp_links = dedupe_strings(
        [
            anchor["href"]
            for anchor in anchors
            if any(
                token in anchor["href"].lower()
                for token in ("wa.me", "whatsapp.com", "api.whatsapp.com")
            )
        ]
    )
    contact_page_links = dedupe_strings(
        [
            anchor["href"]
            for anchor in anchors
            if any(token in (anchor.get("text") or "").lower() for token in CONTACT_LINK_KEYWORDS)
            or any(token in anchor["href"].lower() for token in ("/contact", "/contacto"))
        ]
    )
    has_contact_form = any(
        form["hasEmailInput"] or form["hasPhoneInput"] or form["hasTextarea"] for form in forms
    )
    return {
        "emails": email_matches[:5],
        "phones": phone_matches[:5],
        "whatsapp_links": whatsapp_links[:5],
        "contact_page_links": contact_page_links[:5],
        "has_visible_email": bool(email_matches),
        "has_visible_phone": bool(phone_matches),
        "has_whatsapp_link": bool(whatsapp_links),
        "has_contact_form": has_contact_form,
        "has_contact_page_link": bool(contact_page_links),
    }


def extract_social_links(anchors: list[dict[str, str]]) -> dict[str, list[str]]:
    social_links: dict[str, list[str]] = {network: [] for network in SOCIAL_PATTERNS}
    for anchor in anchors:
        href = anchor["href"].lower()
        for network, patterns in SOCIAL_PATTERNS.items():
            if any(pattern in href for pattern in patterns):
                social_links[network].append(anchor["href"])
    return {network: dedupe_strings(urls)[:5] for network, urls in social_links.items()}


def extract_cta_signals(cta_elements: list[str], anchors: list[dict[str, str]]) -> dict[str, Any]:
    labels: list[str] = []
    flags = {
        "has_contact_cta": False,
        "has_quote_cta": False,
        "has_booking_cta": False,
        "has_whatsapp_cta": False,
    }
    for raw_label in cta_elements + [anchor["text"] for anchor in anchors if anchor.get("text")]:
        label = raw_label.strip()
        lower = label.lower()
        if not label:
            continue
        matched = False
        for category, keywords in CTA_KEYWORDS.items():
            if any(keyword in lower for keyword in keywords):
                labels.append(label)
                matched = True
                if category == "contact":
                    flags["has_contact_cta"] = True
                elif category == "quote":
                    flags["has_quote_cta"] = True
                elif category == "book":
                    flags["has_booking_cta"] = True
                elif category == "whatsapp":
                    flags["has_whatsapp_cta"] = True
        if matched and len(labels) >= 12:
            break
    flags["labels"] = dedupe_strings(labels)[:12]
    return flags


def guess_page_type(
    final_url: str,
    anchors: list[dict[str, str]],
    visible_text: str,
    contact_signals: dict[str, Any],
) -> dict[str, Any]:
    lower_text = visible_text.lower()
    hard_hits = sum(contains_keyword_token(lower_text, keyword) for keyword in ("cart", "checkout")) + sum(
        any(contains_keyword_token(anchor["href"], keyword) for keyword in ("cart", "checkout"))
        for anchor in anchors
    )
    soft_hits = sum(contains_keyword_token(lower_text, keyword) for keyword in ECOMMERCE_KEYWORDS) + sum(
        any(
            contains_keyword_token(f"{anchor.get('text', '')} {anchor['href']}", keyword)
            for keyword in ECOMMERCE_KEYWORDS
        )
        for anchor in anchors
    )
    ecommerce_likely = hard_hits > 0 or soft_hits >= 2
    internal_non_hash_links = [
        anchor
        for anchor in anchors
        if anchor["href"].startswith(final_url.rstrip("/"))
        or anchor["href"].startswith("/")
    ]
    hash_links = [anchor for anchor in anchors if "#" in anchor["href"]]
    basic_one_page_likely = (
        len(hash_links) >= 3
        and len(internal_non_hash_links) <= 4
        and not contact_signals["has_contact_form"]
    )
    return {
        "contact_page_present": contact_signals["has_contact_page_link"],
        "ecommerce_likely": ecommerce_likely,
        "basic_one_page_likely": basic_one_page_likely,
    }


def select_important_links(anchors: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    important_keywords = (
        "contact",
        "contacto",
        "about",
        "nosotros",
        "services",
        "servicios",
        "pricing",
        "quote",
        "presupuesto",
        "shop",
        "store",
        "tienda",
    )
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in anchors:
        href = anchor["href"]
        text = anchor.get("text") or ""
        haystack = f"{href} {text}".lower()
        if not any(keyword in haystack for keyword in important_keywords):
            continue
        if href in seen:
            continue
        selected.append({"href": href, "text": text})
        seen.add(href)
        if len(selected) >= limit:
            break
    return selected


def build_summary(
    *,
    final_url: str,
    title: str | None,
    h1: str | None,
    meta_description: str | None,
    contact_signals: dict[str, Any],
    page_type_guess: dict[str, Any],
) -> str:
    parts = [f"final_url={final_url}"]
    if title:
        parts.append(f"title={title}")
    if h1:
        parts.append(f"h1={h1}")
    if meta_description:
        parts.append(f"meta_description={meta_description[:140]}")
    if contact_signals["has_visible_email"]:
        parts.append("visible_email=yes")
    if contact_signals["has_visible_phone"]:
        parts.append("visible_phone=yes")
    if contact_signals["has_whatsapp_link"]:
        parts.append("whatsapp_link=yes")
    if contact_signals["has_contact_form"]:
        parts.append("contact_form=yes")
    if page_type_guess["ecommerce_likely"]:
        parts.append("ecommerce_likely=yes")
    if page_type_guess["basic_one_page_likely"]:
        parts.append("basic_one_page_likely=yes")
    return "; ".join(parts)


def inspect_url(
    input_url: str,
    *,
    timeout_ms: int,
    screenshot: bool,
    screenshot_dir: str,
    links_limit: int,
) -> dict[str, Any]:
    input_url = ensure_url(input_url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        navigation_response = page.goto(input_url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 5000))
        except PlaywrightTimeoutError:
            pass

        snapshot = collect_page_snapshot(page)
        final_url = page.url
        visible_text = (snapshot["visibleText"] or "").replace("\x00", " ")
        anchors = snapshot["anchors"] or []
        forms = snapshot["forms"] or []
        cta_elements = snapshot["ctaElements"] or []
        contact_signals = extract_contact_signals(visible_text, anchors, forms)
        social_links = extract_social_links(anchors)
        cta_signals = extract_cta_signals(cta_elements, anchors)
        page_type_guess = guess_page_type(final_url, anchors, visible_text, contact_signals)
        important_links = select_important_links(anchors, links_limit)
        screenshot_path: str | None = None
        if screenshot:
            directory = Path(screenshot_dir).expanduser()
            directory.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", parse.urlparse(final_url).netloc or "site").strip("-")
            screenshot_path = str(
                directory / f"{safe_name or 'site'}-{time.strftime('%Y%m%d_%H%M%S')}.png"
            )
            page.screenshot(path=screenshot_path, full_page=True)

        title = snapshot["title"] or None
        meta_description = snapshot["metaDescription"] or None
        h1 = snapshot["h1"] or None
        result = {
            "input_url": input_url,
            "final_url": final_url,
            "navigation": {
                "success": True,
                "status_code": navigation_response.status if navigation_response else None,
            },
            "title": title,
            "meta_description": meta_description,
            "h1": h1,
            "contact_signals": contact_signals,
            "social_links": social_links,
            "cta_signals": cta_signals,
            "page_type_guess": page_type_guess,
            "important_links": important_links,
            "visible_text_snippet": visible_text[:500].strip() or None,
            "screenshot_path": screenshot_path,
        }
        result["extracted_summary"] = build_summary(
            final_url=final_url,
            title=title,
            h1=h1,
            meta_description=meta_description,
            contact_signals=contact_signals,
            page_type_guess=page_type_guess,
        )
        context.close()
        browser.close()
        return result


def main() -> int:
    args = parse_args()
    request_meta: dict[str, Any] = {
        "timeout_ms": args.timeout_ms,
        "screenshot": getattr(args, "screenshot", False),
    }
    try:
        if args.command == "inspect-url":
            request_meta.update({"url": args.url, "links_limit": args.links_limit})
            data = inspect_url(
                args.url,
                timeout_ms=args.timeout_ms,
                screenshot=args.screenshot,
                screenshot_dir=args.screenshot_dir,
                links_limit=args.links_limit,
            )
        elif args.command == "inspect-business-site":
            request_meta.update(
                {
                    "lead_id": args.lead_id,
                    "api_base_url": args.api_base_url,
                    "links_limit": args.links_limit,
                }
            )
            lead = fetch_lead(args.api_base_url, args.lead_id)
            website_url = lead.get("website_url")
            if not website_url:
                payload = error_response(
                    args.command,
                    request_meta,
                    "missing_website",
                    f"Lead {args.lead_id} does not have website_url.",
                    detail={"lead_id": args.lead_id},
                )
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return 1
            data = inspect_url(
                website_url,
                timeout_ms=args.timeout_ms,
                screenshot=args.screenshot,
                screenshot_dir=args.screenshot_dir,
                links_limit=args.links_limit,
            )
            data["lead"] = {
                "id": lead["id"],
                "business_name": lead["business_name"],
                "website_url": lead.get("website_url"),
                "status": lead.get("status"),
                "score": lead.get("score"),
                "quality": lead.get("quality"),
            }
            request_meta["url"] = website_url
            request_meta["lead_endpoint"] = f"{args.api_base_url.rstrip('/')}/leads/{args.lead_id}"
        else:
            raise ValueError(f"Unsupported command: {args.command}")

        payload = ok_response(args.command, request_meta, data)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (PlaywrightTimeoutError, PlaywrightError) as exc:
        payload = error_response(
            args.command,
            request_meta,
            "browser_error",
            str(exc),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    except RuntimeError as exc:
        payload = error_response(args.command, request_meta, "runtime_error", str(exc))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    except Exception as exc:  # pragma: no cover - defensive wrapper
        payload = error_response(args.command, request_meta, "unexpected_error", str(exc))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
