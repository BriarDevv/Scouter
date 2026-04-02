"""Sanitize external data before passing to LLM prompts.

Strips HTML tags, dangerous patterns, and enforces length limits to mitigate
prompt injection from crawled/scraped content (PI-6/7/8).
"""

import re

# Max chars per field passed to LLM
_MAX_FIELD_LENGTH = 2000
_MAX_TOTAL_DATA_LENGTH = 10000

# Patterns to strip from external data
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(
    r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE
)
_STYLE_RE = re.compile(
    r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE
)
_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(previous|above|all)\s+instructions"
    r"|you\s+are\s+now\s+a"
    r"|disregard\s+(all|your)\s+previous"
    r"|forget\s+(everything|all)\s+(you|your)"
    r"|system\s*:\s*you\s+are"
    r"|<\s*/?\s*system\s*>"
    r"|IMPORTANT:\s*ignore)",
    re.IGNORECASE,
)


def sanitize_field(
    value: str | None, max_length: int = _MAX_FIELD_LENGTH
) -> str:
    """Sanitize a single field value for LLM consumption."""
    if not value:
        return ""
    text = str(value)
    # Remove script/style blocks first
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    # Remove HTML tags
    text = _HTML_TAG_RE.sub(" ", text)
    # Remove known injection patterns
    text = _INJECTION_PATTERNS.sub("[REDACTED]", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text


def sanitize_data_block(
    text: str, max_length: int = _MAX_TOTAL_DATA_LENGTH
) -> str:
    """Sanitize a complete data block (the formatted data prompt)."""
    result = sanitize_field(text, max_length)
    return result
