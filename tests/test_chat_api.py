"""Tests for chat API endpoints and conversation management."""

import uuid


def test_create_conversation(client):
    resp = client.post("/api/v1/chat/conversations")
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["channel"] == "web"
    assert data["is_active"] is True


def test_list_conversations(client):
    # Create one first
    client.post("/api/v1/chat/conversations")
    resp = client.get("/api/v1/chat/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_conversation_detail(client):
    create_resp = client.post("/api/v1/chat/conversations")
    conv_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == conv_id
    assert "messages" in data


def test_get_nonexistent_conversation_returns_404(client):
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/chat/conversations/{fake_id}")
    assert resp.status_code == 404


def test_delete_conversation(client):
    create_resp = client.post("/api/v1/chat/conversations")
    conv_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert resp.status_code == 204


def test_delete_nonexistent_conversation_returns_404(client):
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/chat/conversations/{fake_id}")
    assert resp.status_code == 404
