"""Regression tests for Slack Incoming Webhook alerts.

Closes the gap from docs/roadmaps/post-hardening-plan.md Item 4 (the part
not already covered by Telegram+WhatsApp): critical notifications can now
be dispatched to a Slack webhook in addition to the existing channels.

Contract:
- slack_service.send_alert returns True on HTTP 200, False otherwise, never raises
- notification_service._maybe_dispatch_slack gates on slack_alerts_enabled +
  slack_min_severity threshold
- Failures update Notification.channel_state but never prevent row creation
"""

from unittest.mock import patch

import httpx

from app.models.notification import NotificationCategory, NotificationSeverity
from app.models.settings import OperationalSettings
from app.services.comms.slack_service import send_alert
from app.services.notifications.notification_service import create_notification


def _enable_slack(
    db,
    *,
    webhook_url: str = "https://hooks.slack.com/services/FAKE/WEBHOOK/URL",
    min_severity: str = "high",
):
    ops = db.get(OperationalSettings, 1)
    if ops is None:
        ops = OperationalSettings(id=1)
        db.add(ops)
    ops.slack_alerts_enabled = True
    ops.slack_webhook_url = webhook_url
    ops.slack_min_severity = min_severity
    db.commit()


class _FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    """Httpx-compatible context manager that captures the POST payload."""

    captured: list[dict] = []
    status_code: int = 200
    raise_exc: Exception | None = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json):
        _FakeClient.captured.append({"url": url, "json": json})
        if _FakeClient.raise_exc is not None:
            raise _FakeClient.raise_exc
        return _FakeResponse(_FakeClient.status_code)


def _reset_fake_client():
    _FakeClient.captured = []
    _FakeClient.status_code = 200
    _FakeClient.raise_exc = None


def test_send_alert_returns_true_on_http_200(db):
    _enable_slack(db)
    _reset_fake_client()
    _FakeClient.status_code = 200

    with patch("app.services.comms.slack_service.httpx.Client", _FakeClient):
        ok = send_alert(db, title="Pipeline stopped", message="No leads", severity="critical")

    assert ok is True
    assert len(_FakeClient.captured) == 1
    call = _FakeClient.captured[0]
    assert call["url"].startswith("https://hooks.slack.com/")
    assert "Pipeline stopped" in call["json"]["text"]


def test_send_alert_returns_false_on_http_500(db):
    _enable_slack(db)
    _reset_fake_client()
    _FakeClient.status_code = 500

    with patch("app.services.comms.slack_service.httpx.Client", _FakeClient):
        ok = send_alert(db, title="Test", message="test", severity="high")

    assert ok is False


def test_send_alert_returns_false_without_webhook_url(db):
    ops = db.get(OperationalSettings, 1)
    if ops is None:
        ops = OperationalSettings(id=1)
        db.add(ops)
    ops.slack_alerts_enabled = True
    ops.slack_webhook_url = None
    db.commit()

    with patch("app.services.comms.slack_service.httpx.Client", _FakeClient):
        ok = send_alert(db, title="Test", message="test", severity="critical")

    assert ok is False


def test_dispatch_slack_respects_severity_threshold(db):
    _enable_slack(db, min_severity="critical")
    _reset_fake_client()

    with patch("app.services.comms.slack_service.httpx.Client", _FakeClient):
        # severity=high is BELOW threshold critical → no dispatch
        notif = create_notification(
            db,
            type="test_event",
            category=NotificationCategory.SYSTEM,
            severity=NotificationSeverity.HIGH,
            title="High severity",
            message="Should not dispatch",
        )

    assert notif is not None
    assert len(_FakeClient.captured) == 0
    # No slack entry in channel_state since dispatch was skipped by threshold
    assert "slack" not in (notif.channel_state or {})


def test_dispatch_slack_survives_http_exception(db):
    """Exception during HTTP POST must NOT prevent Notification row creation."""
    _enable_slack(db)
    _reset_fake_client()
    _FakeClient.raise_exc = httpx.ConnectError("broker offline")

    with patch("app.services.comms.slack_service.httpx.Client", _FakeClient):
        notif = create_notification(
            db,
            type="test_crash",
            category=NotificationCategory.SYSTEM,
            severity=NotificationSeverity.CRITICAL,
            title="Crit",
            message="crit body",
        )

    # Row must still exist
    assert notif is not None
    # channel_state reflects failure (either 'failed' from send_alert's return-False path
    # or 'failed' from the wrapper exception path — both are acceptable)
    assert notif.channel_state.get("slack") == "failed"
