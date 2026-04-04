import logging
import re
import sys

import structlog

from app.core.config import settings

_SENSITIVE_KEY_RE = re.compile(
    r"(password|secret|token|authorization|smtp_password|imap_password|api.?key)",
    re.IGNORECASE,
)


def _scrub_sensitive_keys(
    logger: object, method_name: str, event_dict: dict
) -> dict:
    """Remove values of keys that look like secrets from log events."""
    for key in list(event_dict):
        if _SENSITIVE_KEY_RE.search(key):
            event_dict[key] = "***REDACTED***"
    return event_dict


def setup_logging() -> None:
    """Configure structlog for structured JSON logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _scrub_sensitive_keys,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if settings.APP_ENV == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
