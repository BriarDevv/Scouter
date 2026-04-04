from datetime import UTC, datetime

from app.core.config import settings
from app.models.inbound_mail import InboundMailSyncRun


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


def test_mail_settings_endpoint_returns_non_sensitive_mail_state(client, db, monkeypatch):
    monkeypatch.setattr(settings, "MAIL_PROVIDER", "smtp")
    monkeypatch.setattr(settings, "MAIL_ENABLED", True)
    monkeypatch.setattr(settings, "MAIL_FROM_EMAIL", "sales@scouter.local")
    monkeypatch.setattr(settings, "MAIL_FROM_NAME", "Scouter Sales")
    monkeypatch.setattr(settings, "MAIL_REPLY_TO", "replies@scouter.local")
    monkeypatch.setattr(settings, "MAIL_SEND_TIMEOUT", 45)
    monkeypatch.setattr(settings, "MAIL_SMTP_HOST", "smtp.local")
    monkeypatch.setattr(settings, "MAIL_SMTP_USERNAME", "sales@scouter.local")
    monkeypatch.setattr(settings, "MAIL_SMTP_PASSWORD", "super-secret")
    monkeypatch.setattr(settings, "MAIL_INBOUND_PROVIDER", "imap")
    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", True)
    monkeypatch.setattr(settings, "MAIL_IMAP_HOST", "imap.local")
    monkeypatch.setattr(settings, "MAIL_IMAP_USERNAME", "inbox@scouter.local")
    monkeypatch.setattr(settings, "MAIL_IMAP_PASSWORD", "imap-secret")
    monkeypatch.setattr(settings, "MAIL_IMAP_MAILBOX", "INBOX")
    monkeypatch.setattr(settings, "MAIL_IMAP_SEARCH_CRITERIA", "ALL")
    monkeypatch.setattr(settings, "MAIL_INBOUND_SYNC_LIMIT", 50)
    monkeypatch.setattr(settings, "MAIL_INBOUND_TIMEOUT", 20)
    monkeypatch.setattr(settings, "MAIL_AUTO_CLASSIFY_INBOUND", True)
    monkeypatch.setattr(settings, "MAIL_USE_REVIEWER_FOR_LABELS", "needs_human_review,asked_for_quote")

    # The mail settings endpoint reads auto_classify_inbound from DB, not env.
    from app.services.settings.operational_settings_service import get_or_create
    ops = get_or_create(db)
    ops.auto_classify_inbound = True
    db.commit()

    sync_run = InboundMailSyncRun(
        provider="imap",
        provider_mailbox="INBOX",
        status="completed",
        fetched_count=12,
        new_count=4,
        deduplicated_count=3,
        matched_count=2,
        unmatched_count=2,
        completed_at=datetime.now(UTC),
    )
    db.add(sync_run)
    db.commit()

    response = client.get("/api/v1/settings/mail")
    assert response.status_code == 200

    payload = response.json()
    assert payload["read_only"] is False
    assert payload["editable"] is True
    assert payload["outbound"]["enabled"] is True
    assert payload["outbound"]["provider"] == "smtp"
    assert payload["outbound"]["from_email"] == "sales@scouter.local"
    assert payload["outbound"]["from_name"] == "Scouter Sales"
    assert payload["outbound"]["reply_to"] == "replies@scouter.local"
    assert payload["outbound"]["send_timeout_seconds"] == 45
    assert payload["outbound"]["require_approved_drafts"] is True
    assert payload["outbound"]["configured"] is True
    assert payload["outbound"]["ready"] is True
    assert payload["inbound"]["enabled"] is True
    assert payload["inbound"]["provider"] == "imap"
    assert payload["inbound"]["account"] == "inbox@scouter.local"
    assert payload["inbound"]["mailbox"] == "INBOX"
    assert payload["inbound"]["sync_limit"] == 50
    assert payload["inbound"]["timeout_seconds"] == 20
    assert payload["inbound"]["auto_classify_inbound"] is True
    assert payload["inbound"]["use_reviewer_for_labels"] == [
        "needs_human_review",
        "asked_for_quote",
    ]
    assert payload["inbound"]["last_sync"]["status"] == "completed"
    assert payload["inbound"]["last_sync"]["counts"]["fetched"] == 12
    assert payload["health"]["outbound_ready"] is True
    assert payload["health"]["inbound_ready"] is True
    assert "MAIL_SMTP_PASSWORD" not in payload
    assert "MAIL_IMAP_PASSWORD" not in payload
    assert "super-secret" not in response.text
    assert "imap-secret" not in response.text


def test_mail_settings_endpoint_reports_missing_secret_backed_requirements(client, monkeypatch):
    monkeypatch.setattr(settings, "MAIL_ENABLED", False)
    monkeypatch.setattr(settings, "MAIL_PROVIDER", "smtp")
    monkeypatch.setattr(settings, "MAIL_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "MAIL_SMTP_HOST", None)
    monkeypatch.setattr(settings, "MAIL_SMTP_USERNAME", None)
    monkeypatch.setattr(settings, "MAIL_SMTP_PASSWORD", None)
    monkeypatch.setattr(settings, "MAIL_INBOUND_ENABLED", False)
    monkeypatch.setattr(settings, "MAIL_IMAP_HOST", None)
    monkeypatch.setattr(settings, "MAIL_IMAP_USERNAME", None)
    monkeypatch.setattr(settings, "MAIL_IMAP_PASSWORD", None)

    response = client.get("/api/v1/settings/mail")
    assert response.status_code == 200

    payload = response.json()
    assert payload["outbound"]["configured"] is False
    assert payload["outbound"]["ready"] is False
    assert "MAIL_SMTP_PASSWORD" in payload["outbound"]["missing_requirements"]
    assert payload["inbound"]["configured"] is False
    assert payload["inbound"]["ready"] is False
    assert "MAIL_IMAP_PASSWORD" in payload["inbound"]["missing_requirements"]
    assert payload["inbound"]["last_sync"] is None
