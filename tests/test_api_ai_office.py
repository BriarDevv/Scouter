"""Tests for /ai-office API endpoints."""


def test_ai_office_status_returns_agent_overview(client):
    response = client.get("/api/v1/ai-office/status")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    agents = data["agents"]
    assert "mote" in agents
    assert "scout" in agents
    assert "executor" in agents
    assert "reviewer" in agents
    assert agents["mote"]["model"] == "hermes3:8b"
    assert "outcomes" in data


def test_ai_office_decisions_returns_list(client):
    response = client.get("/api/v1/ai-office/decisions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_ai_office_investigations_returns_list(client):
    response = client.get("/api/v1/ai-office/investigations?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_ai_office_conversations_returns_list(client):
    response = client.get("/api/v1/ai-office/conversations?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_ai_office_weekly_reports_returns_list(client):
    response = client.get("/api/v1/ai-office/weekly-reports?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_ai_office_test_send_whatsapp_validates_phone(client):
    """POST body with invalid phone should return 422."""
    response = client.post(
        "/api/v1/ai-office/test-send-whatsapp",
        json={"phone": "123", "message": "test"},
    )
    assert response.status_code == 422


def test_ai_office_test_send_whatsapp_accepts_valid_body(client, monkeypatch):
    """POST with valid phone should attempt to send (mock Kapso)."""
    def fake_send(phone, message):
        return {"message_id": "wamid.TEST"}

    monkeypatch.setattr(
        "app.services.comms.kapso_service.send_text_message",
        fake_send,
    )

    response = client.post(
        "/api/v1/ai-office/test-send-whatsapp",
        json={"phone": "+5491158399708", "message": "Test message"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert data["message_id"] == "wamid.TEST"
    assert "***" in data["phone"]  # masked


def test_ai_office_conversation_not_found(client):
    import uuid
    response = client.get(f"/api/v1/ai-office/conversations/{uuid.uuid4()}")
    assert response.status_code == 404
