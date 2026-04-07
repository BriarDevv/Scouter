"""Tests for the mail credentials settings API."""


def test_get_mail_credentials_defaults(client):
    resp = client.get("/api/v1/settings/mail-credentials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["smtp_password_set"] is False
    assert data["imap_password_set"] is False
    assert data["smtp_port"] == 587
    assert data["imap_port"] == 993


def test_patch_mail_credentials(client):
    resp = client.patch(
        "/api/v1/settings/mail-credentials",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_username": "user@example.com",
            "smtp_password": "secret123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["smtp_host"] == "smtp.example.com"
    assert data["smtp_username"] == "user@example.com"
    assert data["smtp_password_set"] is True
    # Password itself must never appear in response
    assert "secret123" not in resp.text


def test_patch_mail_credentials_empty_body(client):
    resp = client.patch("/api/v1/settings/mail-credentials", json={})
    assert resp.status_code == 422


def test_test_smtp_connection_no_host(client):
    resp = client.post("/api/v1/settings/test/smtp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"] is not None


def test_test_smtp_connection_with_monkeypatch(client, monkeypatch):
    # Set up credentials first
    client.patch(
        "/api/v1/settings/mail-credentials",
        json={
            "smtp_host": "smtp.test.local",
            "smtp_port": 587,
            "smtp_username": "test@test.local",
            "smtp_password": "pass",
        },
    )

    # Monkeypatch smtplib so it does not actually connect
    import smtplib

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def quit(self):
            pass

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    resp = client.post("/api/v1/settings/test/smtp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["error"] is None


def test_test_imap_connection_no_host(client):
    resp = client.post("/api/v1/settings/test/imap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"] is not None


def test_test_imap_connection_with_monkeypatch(client, monkeypatch):
    # Set up credentials first
    client.patch(
        "/api/v1/settings/mail-credentials",
        json={
            "imap_host": "imap.test.local",
            "imap_port": 993,
            "imap_username": "test@test.local",
            "imap_password": "pass",
            "imap_ssl": True,
        },
    )

    import imaplib

    class FakeIMAP4_SSL:
        def __init__(self, *args, **kwargs):
            pass

        def login(self, user, password):
            pass

        def select(self, mailbox, readonly=False):
            return ("OK", [b"42"])

        def logout(self):
            pass

    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeIMAP4_SSL)

    resp = client.post("/api/v1/settings/test/imap")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["sample_count"] == 42


def test_test_kapso_no_api_key(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "KAPSO_API_KEY", None)

    resp = client.post("/api/v1/settings/test/kapso")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert "KAPSO_API_KEY" in data["message"]


def test_test_kapso_success(client, monkeypatch):
    import httpx

    from app.core.config import settings

    monkeypatch.setattr(settings, "KAPSO_API_KEY", "test-key")
    monkeypatch.setattr(settings, "KAPSO_BASE_URL", "https://kapso.test")

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse())

    resp = client.post("/api/v1/settings/test/kapso")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_test_kapso_auth_failure(client, monkeypatch):
    import httpx

    from app.core.config import settings

    monkeypatch.setattr(settings, "KAPSO_API_KEY", "bad-key")
    monkeypatch.setattr(settings, "KAPSO_BASE_URL", "https://kapso.test")

    class FakeResponse:
        status_code = 401

    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: FakeResponse())

    resp = client.post("/api/v1/settings/test/kapso")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "error"
    assert "inv" in data["message"].lower() or "perm" in data["message"].lower()
