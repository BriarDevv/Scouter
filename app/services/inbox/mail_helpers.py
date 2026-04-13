"""Shared helper functions for inbound mail processing.

Normalisation utilities for message IDs, email addresses, and subjects,
plus reference-ID extraction from RFC 2822 References headers.
"""

from __future__ import annotations

import re

SUBJECT_PREFIX_RE = re.compile(r"^(?:(?:re|fw|fwd)\s*:\s*)+", re.IGNORECASE)
BRACKETED_TAG_RE = re.compile(r"\[\w+\]", re.IGNORECASE)
MESSAGE_ID_RE = re.compile(r"<([^>]+)>")


def normalize_message_id(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1]
    normalized = normalized.strip()
    return normalized or None


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized or None


def normalize_subject(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    # Strip bracketed noise tags like [EXTERNAL], [SPAM], etc.
    normalized = BRACKETED_TAG_RE.sub("", normalized)
    # Strip reply/forward prefixes (Re:, Fwd:, FW:, RE:, etc.)
    normalized = SUBJECT_PREFIX_RE.sub("", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized or None


def extract_reference_ids(raw_references: str | None) -> list[str]:
    if not raw_references:
        return []
    matches = [match.strip() for match in MESSAGE_ID_RE.findall(raw_references)]
    if matches:
        normalized_matches: list[str] = []
        for match in matches:
            normalized = normalize_message_id(match)
            if normalized:
                normalized_matches.append(normalized)
        return normalized_matches
    normalized_tokens: list[str] = []
    for token in raw_references.split():
        normalized = normalize_message_id(token)
        if normalized:
            normalized_tokens.append(normalized)
    return normalized_tokens
