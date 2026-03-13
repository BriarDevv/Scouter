from app.core.config import settings


def test_llm_settings_endpoint_returns_role_models(client, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen3.5:9b")
    monkeypatch.setattr(settings, "OLLAMA_SUPPORTED_MODELS", "qwen3.5:4b,qwen3.5:9b,qwen3.5:27b")
    monkeypatch.setattr(settings, "OLLAMA_LEADER_MODEL", "qwen3.5:4b")
    monkeypatch.setattr(settings, "OLLAMA_EXECUTOR_MODEL", None)
    monkeypatch.setattr(settings, "OLLAMA_REVIEWER_MODEL", "qwen3.5:27b")
    monkeypatch.setattr(settings, "OLLAMA_TIMEOUT", 120)
    monkeypatch.setattr(settings, "OLLAMA_MAX_RETRIES", 3)

    response = client.get("/api/v1/settings/llm")
    assert response.status_code == 200

    payload = response.json()
    assert payload["provider"] == "ollama"
    assert payload["leader_model"] == "qwen3.5:4b"
    assert payload["executor_model"] == "qwen3.5:9b"
    assert payload["reviewer_model"] == "qwen3.5:27b"
    assert payload["supported_models"] == ["qwen3.5:4b", "qwen3.5:9b", "qwen3.5:27b"]
    assert payload["legacy_executor_fallback_model"] == "qwen3.5:9b"
    assert payload["legacy_executor_fallback_active"] is True
    assert payload["read_only"] is True
    assert payload["editable"] is False
    assert payload["default_role_models"]["leader"] == "qwen3.5:4b"
    assert payload["default_role_models"]["executor"] == "qwen3.5:9b"
    assert payload["default_role_models"]["reviewer"] == "qwen3.5:27b"


def test_llm_settings_endpoint_marks_executor_override(client, monkeypatch):
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "qwen3.5:9b")
    monkeypatch.setattr(settings, "OLLAMA_EXECUTOR_MODEL", "qwen3.5:27b")

    response = client.get("/api/v1/settings/llm")
    assert response.status_code == 200

    payload = response.json()
    assert payload["executor_model"] == "qwen3.5:27b"
    assert payload["legacy_executor_fallback_model"] == "qwen3.5:9b"
    assert payload["legacy_executor_fallback_active"] is False
