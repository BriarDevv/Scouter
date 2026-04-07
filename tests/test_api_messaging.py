"""Tests for the messaging settings API (WhatsApp + Telegram credentials)."""


def test_get_whatsapp_credentials_defaults(client):
    resp = client.get("/api/v1/settings/whatsapp-credentials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "callmebot"
    assert data["api_key_set"] is False
    assert data["webhook_secret_set"] is False


def test_patch_whatsapp_credentials(client):
    resp = client.patch(
        "/api/v1/settings/whatsapp-credentials",
        json={
            "phone_number": "+5491155551234",
            "provider": "callmebot",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone_number"] == "+5491155551234"
    assert data["provider"] == "callmebot"


def test_patch_whatsapp_credentials_empty(client):
    resp = client.patch("/api/v1/settings/whatsapp-credentials", json={})
    assert resp.status_code == 422


def test_get_telegram_credentials_defaults(client):
    resp = client.get("/api/v1/settings/telegram-credentials")
    assert resp.status_code == 200
    data = resp.json()
    assert data["bot_token_set"] is False
    assert data["webhook_secret_set"] is False
    assert data["bot_username"] is None


def test_patch_telegram_credentials(client):
    resp = client.patch(
        "/api/v1/settings/telegram-credentials",
        json={
            "bot_username": "scouter_bot",
            "chat_id": "123456789",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bot_username"] == "scouter_bot"
    assert data["chat_id"] == "123456789"


def test_patch_telegram_credentials_empty(client):
    resp = client.patch("/api/v1/settings/telegram-credentials", json={})
    assert resp.status_code == 422


def test_test_whatsapp_no_phone(client):
    resp = client.post("/api/v1/settings/test/whatsapp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "numero" in data["error"].lower() or "phone" in data["error"].lower()


def test_test_telegram_no_token(client):
    resp = client.post("/api/v1/settings/test/telegram")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "token" in data["error"].lower()


def test_register_telegram_webhook_no_token(client):
    resp = client.post(
        "/api/v1/settings/telegram/register-webhook",
        json={"webhook_url": "https://example.com/webhook"},
    )
    assert resp.status_code == 400


def test_register_telegram_webhook_success(db, client, monkeypatch):
    from app.models.telegram_credentials import TelegramCredentials

    creds = TelegramCredentials(id=1, bot_token="fake-token")
    db.merge(creds)
    db.commit()

    monkeypatch.setattr(
        "app.api.v1.settings.messaging._call_telegram",
        lambda token, method, payload=None: {"ok": True},
    )

    resp = client.post(
        "/api/v1/settings/telegram/register-webhook",
        json={"webhook_url": "https://example.com/tg-webhook"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "example.com" in data["message"]


def test_register_telegram_webhook_api_error(db, client, monkeypatch):
    from app.models.telegram_credentials import TelegramCredentials

    creds = TelegramCredentials(id=1, bot_token="fake-token")
    db.merge(creds)
    db.commit()

    monkeypatch.setattr(
        "app.api.v1.settings.messaging._call_telegram",
        lambda token, method, payload=None: {
            "ok": False,
            "description": "Bad Request",
        },
    )

    resp = client.post(
        "/api/v1/settings/telegram/register-webhook",
        json={"webhook_url": "https://example.com/tg-webhook"},
    )
    assert resp.status_code == 502
