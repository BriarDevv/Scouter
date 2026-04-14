"""Slack Incoming Webhook service for critical alerts.

Simpler than Telegram (Bot API): just POST a JSON payload to the webhook URL.
No credentials table, no OAuth — the URL itself is the secret and is stored
in OperationalSettings.slack_webhook_url.
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)

_SEND_TIMEOUT = 10

_SEVERITY_COLORS = {
    "info": "#36a64f",  # green
    "warning": "#ffcc00",  # yellow
    "high": "#ff8c00",  # orange
    "critical": "#ff0000",  # red
}


def send_alert(db: Session, *, title: str, message: str, severity: str) -> bool:
    """POST an alert to the configured Slack Incoming Webhook URL.

    Returns True on HTTP 200, False otherwise (bad config, non-200, network).
    Never raises.
    """
    from app.services.settings.operational_settings_service import get_cached_settings

    try:
        ops = get_cached_settings(db)
    except Exception as exc:
        logger.error("slack_settings_unavailable", error=str(exc))
        return False

    webhook_url = getattr(ops, "slack_webhook_url", None)
    if not webhook_url:
        logger.debug("slack_send_skipped_no_webhook_url")
        return False

    color = _SEVERITY_COLORS.get(severity, "#808080")
    payload = {
        "text": f"*{title}*",
        "attachments": [
            {
                "color": color,
                "fields": [
                    {"title": "Severity", "value": severity, "short": True},
                    {"title": "Message", "value": message, "short": False},
                ],
            }
        ],
    }

    try:
        with httpx.Client(timeout=_SEND_TIMEOUT) as client:
            resp = client.post(webhook_url, json=payload)
        if resp.status_code == 200:
            logger.info("slack_alert_sent", severity=severity)
            return True
        logger.warning(
            "slack_alert_non_200",
            status_code=resp.status_code,
            body=resp.text[:200],
        )
        return False
    except Exception as exc:
        logger.error("slack_alert_exception", error=str(exc), exc_type=type(exc).__name__)
        return False
