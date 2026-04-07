"""Tests for WhatsApp and Telegram webhook endpoints."""


# ── WhatsApp Webhook ─────────────────────────────────────────────


def test_whatsapp_webhook_verify(client):
    resp = client.get("/api/v1/whatsapp/webhook?hub.challenge=test-challenge-123")
    assert resp.status_code == 200
    assert resp.json()["challenge"] == "test-challenge-123"


def test_whatsapp_webhook_verify_empty(client):
    resp = client.get("/api/v1/whatsapp/webhook")
    assert resp.status_code == 200
    assert resp.json()["challenge"] == ""


def test_whatsapp_webhook_post_no_secret(client):
    resp = client.post(
        "/api/v1/whatsapp/webhook",
        json={"phone": "+5491100001111", "message": "Hola"},
    )
    assert resp.status_code == 403


def test_whatsapp_webhook_post_bad_secret(db, client):
    from app.models.whatsapp_credentials import WhatsAppCredentials

    creds = WhatsAppCredentials(id=1, webhook_secret="correct-secret")
    db.merge(creds)
    db.commit()

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        json={"phone": "+5491100001111", "message": "Hola"},
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert resp.status_code == 403


def test_whatsapp_webhook_post_agent_disabled(db, client):
    from app.models.settings import OperationalSettings
    from app.models.whatsapp_credentials import WhatsAppCredentials

    creds = WhatsAppCredentials(id=1, webhook_secret="valid-secret")
    db.merge(creds)

    ops = db.get(OperationalSettings, 1)
    if ops:
        ops.whatsapp_agent_enabled = False
    db.commit()

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        json={"phone": "+5491100001111", "message": "Hola"},
        headers={"X-Webhook-Secret": "valid-secret"},
    )
    assert resp.status_code == 403


def test_whatsapp_webhook_post_success(db, client, monkeypatch):
    from app.models.settings import OperationalSettings
    from app.models.whatsapp_credentials import WhatsAppCredentials

    creds = WhatsAppCredentials(id=1, webhook_secret="valid-secret")
    db.merge(creds)

    ops = db.get(OperationalSettings, 1)
    if ops:
        ops.whatsapp_agent_enabled = True
    db.commit()

    monkeypatch.setattr(
        "app.api.v1.whatsapp.handle_channel_message",
        lambda db, channel, channel_id, message: "Respuesta de prueba",
    )
    monkeypatch.setattr(
        "app.api.v1.whatsapp.log_inbound",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.api.v1.whatsapp.log_outbound",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.api.v1.whatsapp.send_alert",
        lambda *args, **kwargs: True,
    )

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        json={"phone": "+5491100001111", "message": "Hola test"},
        headers={"X-Webhook-Secret": "valid-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["response"] == "Respuesta de prueba"


# ── Telegram Webhook ─────────────────────────────────────────────


def test_telegram_webhook_empty_update(client):
    """An update with no message should return ok=True silently."""
    resp = client.post("/api/v1/telegram/webhook", json={})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_telegram_webhook_no_secret(db, client):
    from app.models.telegram_credentials import TelegramCredentials

    creds = TelegramCredentials(id=1, webhook_secret="tg-secret")
    db.merge(creds)
    db.commit()

    resp = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {"text": "Hola", "chat": {"id": 12345}},
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )
    assert resp.status_code == 403


def test_telegram_webhook_agent_disabled(db, client):
    from app.models.settings import OperationalSettings
    from app.models.telegram_credentials import TelegramCredentials

    creds = TelegramCredentials(id=1, webhook_secret="tg-secret")
    db.merge(creds)

    ops = db.get(OperationalSettings, 1)
    if ops:
        ops.telegram_agent_enabled = False
    db.commit()

    resp = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {"text": "Hola", "chat": {"id": 12345}},
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": "tg-secret"},
    )
    assert resp.status_code == 403


def test_telegram_webhook_success(db, client, monkeypatch):
    from app.models.settings import OperationalSettings
    from app.models.telegram_credentials import TelegramCredentials

    creds = TelegramCredentials(id=1, webhook_secret="tg-secret")
    db.merge(creds)

    ops = db.get(OperationalSettings, 1)
    if ops:
        ops.telegram_agent_enabled = True
    db.commit()

    monkeypatch.setattr(
        "app.api.v1.telegram.handle_channel_message",
        lambda db, channel, channel_id, message: "Respuesta telegram",
    )
    monkeypatch.setattr(
        "app.api.v1.telegram.log_inbound",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.api.v1.telegram.log_outbound",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.api.v1.telegram.tg_send_message",
        lambda *args, **kwargs: True,
    )

    resp = client.post(
        "/api/v1/telegram/webhook",
        json={
            "message": {"text": "Hola telegram", "chat": {"id": 99999}},
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": "tg-secret"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
