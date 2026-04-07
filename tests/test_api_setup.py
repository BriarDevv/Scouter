from app.services.settings.setup_service import REPO_ROOT


def test_setup_readiness_endpoint_aggregates_runtime_and_config(client, db, monkeypatch):
    monkeypatch.setattr(
        "app.services.settings.setup_service._current_platform",
        lambda: "windows-wsl",
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service.get_system_health",
        lambda db: {
            "status": "healthy",
            "components": [
                {"name": "database", "status": "ok", "latency_ms": 1.0, "error": None},
                {"name": "redis", "status": "ok", "latency_ms": 1.0, "error": None},
                {"name": "ollama", "status": "ok", "latency_ms": 1.0, "error": None},
                {"name": "celery", "status": "ok", "latency_ms": 1.0, "error": None},
            ],
        },
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service.get_setup_status",
        lambda db: {
            "steps": [
                {"id": "brand", "label": "Marca", "status": "complete", "detail": None, "action": None},
                {"id": "whatsapp", "label": "WhatsApp", "status": "complete", "detail": None, "action": None},
                {"id": "mail_out", "label": "SMTP", "status": "complete", "detail": None, "action": None},
                {"id": "mail_in", "label": "IMAP", "status": "complete", "detail": None, "action": None},
                {"id": "telegram", "label": "Telegram", "status": "incomplete", "detail": None, "action": None},
                {"id": "rules", "label": "Reglas", "status": "complete", "detail": None, "action": None},
            ],
            "overall": "ready",
            "ready_to_send": True,
            "ready_to_receive": True,
            "has_outreach_channel": True,
        },
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service._update_status",
        lambda: {
            "supported": True,
            "current_branch": "main",
            "updates_available": False,
            "dirty": False,
            "can_autopull": False,
            "detail": "ok",
        },
    )

    response = client.get("/api/v1/setup/readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall"] == "ready"
    assert payload["dashboard_unlocked"] is True
    assert payload["hermes_unlocked"] is True
    assert payload["recommended_route"] == "/"
    assert payload["target_platform"] == "windows-wsl"
    assert payload["current_platform"] == "windows-wsl"
    assert payload["wizard_steps"] == []
    assert len(payload["platform_steps"]) == 1
    assert len(payload["runtime_steps"]) == 4
    assert len(payload["config_steps"]) == 6
    assert {item["id"] for item in payload["actions"]} == {"refresh", "preflight", "start_stack"}


def test_setup_readiness_endpoint_blocks_unsupported_platform_and_derives_wizard(
    client, db, monkeypatch
):
    monkeypatch.setattr(
        "app.services.settings.setup_service._current_platform",
        lambda: "linux",
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service.get_system_health",
        lambda db: {
            "status": "degraded",
            "components": [
                {"name": "database", "status": "ok", "latency_ms": None, "error": None},
                {"name": "redis", "status": "ok", "latency_ms": None, "error": None},
                {"name": "ollama", "status": "error", "latency_ms": None, "error": "down"},
                {"name": "celery", "status": "degraded", "latency_ms": None, "error": "no workers"},
            ],
        },
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service.get_setup_status",
        lambda db: {
            "steps": [
                {"id": "brand", "label": "Marca", "status": "incomplete", "detail": "Falta", "action": "Completar"},
                {"id": "whatsapp", "label": "WhatsApp", "status": "incomplete", "detail": "Falta", "action": "Configurar"},
                {"id": "mail_out", "label": "SMTP", "status": "warning", "detail": "Sin probar", "action": "Probar"},
                {"id": "mail_in", "label": "IMAP", "status": "incomplete", "detail": "Falta", "action": "Completar"},
                {"id": "telegram", "label": "Telegram", "status": "incomplete", "detail": "Falta", "action": "Configurar"},
                {"id": "rules", "label": "Reglas", "status": "complete", "detail": None, "action": None},
            ],
            "overall": "incomplete",
            "ready_to_send": False,
            "ready_to_receive": False,
            "has_outreach_channel": False,
        },
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service._update_status",
        lambda: {
            "supported": True,
            "current_branch": "main",
            "updates_available": False,
            "dirty": True,
            "can_autopull": False,
            "detail": "dirty",
        },
    )

    response = client.get("/api/v1/setup/readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall"] == "blocked"
    assert payload["dashboard_unlocked"] is False
    assert payload["recommended_route"] == "/onboarding"
    assert "brand" in payload["wizard_steps"]
    # At least one outreach channel should appear in wizard
    assert "whatsapp" in payload["wizard_steps"] or "credentials" in payload["wizard_steps"]
    assert payload["updates"]["updates_available"] is False
    assert payload["updates"]["can_autopull"] is False


def test_setup_action_refresh_is_safe_noop(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.setup._ACTION_COOLDOWN_SECONDS", 0.0)
    response = client.post("/api/v1/setup/actions/refresh")
    assert response.status_code == 200
    payload = response.json()
    assert payload["action_id"] == "refresh"
    assert payload["status"] == "completed"


def test_setup_action_preflight_runs_whitelisted_command(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.setup._ACTION_COOLDOWN_SECONDS", 0.0)
    captured = {}

    def fake_run_command(cmd, timeout):
        captured["cmd"] = cmd
        captured["timeout"] = timeout
        return "completed", "preflight ok"

    monkeypatch.setattr("app.services.settings.setup_service._run_command", fake_run_command)

    response = client.post("/api/v1/setup/actions/preflight")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert "preflight" in payload["summary"].lower()
    assert captured["cmd"] == [str(REPO_ROOT / ".venv" / "bin" / "python"), "scripts/preflight.py"]
    assert captured["timeout"] == 120



def test_setup_readiness_exposes_update_action_only_when_autopull_is_possible(
    client, db, monkeypatch
):
    monkeypatch.setattr("app.services.settings.setup_service._current_platform", lambda: "windows-wsl")
    monkeypatch.setattr(
        "app.services.settings.setup_service.get_system_health",
        lambda db: {
            "status": "healthy",
            "components": [
                {"name": "database", "status": "ok", "latency_ms": 1.0, "error": None},
                {"name": "redis", "status": "ok", "latency_ms": 1.0, "error": None},
                {"name": "ollama", "status": "ok", "latency_ms": 1.0, "error": None},
                {"name": "celery", "status": "ok", "latency_ms": 1.0, "error": None},
            ],
        },
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service.get_setup_status",
        lambda db: {
            "steps": [
                {
                    "id": "brand",
                    "label": "Marca",
                    "status": "complete",
                    "detail": None,
                    "action": None,
                },
                {
                    "id": "mail_out",
                    "label": "SMTP",
                    "status": "complete",
                    "detail": None,
                    "action": None,
                },
                {
                    "id": "mail_in",
                    "label": "IMAP",
                    "status": "complete",
                    "detail": None,
                    "action": None,
                },
                {
                    "id": "rules",
                    "label": "Reglas",
                    "status": "complete",
                    "detail": None,
                    "action": None,
                },
            ],
            "overall": "ready",
            "ready_to_send": True,
            "ready_to_receive": True,
        },
    )
    monkeypatch.setattr(
        "app.services.settings.setup_service._update_status",
        lambda: {
            "supported": True,
            "current_branch": "main",
            "updates_available": True,
            "dirty": False,
            "can_autopull": True,
            "detail": "update disponible",
        },
    )

    response = client.get("/api/v1/setup/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert {item["id"] for item in payload["actions"]} == {
        "refresh",
        "preflight",
        "start_stack",
        "update_app",
    }
    update_action = next(item for item in payload["actions"] if item["id"] == "update_app")
    assert update_action["kind"] == "manual"
    assert "git pull --ff-only" in update_action["manual_instructions"]


def test_setup_action_rejects_unknown_action(client, monkeypatch):
    monkeypatch.setattr("app.api.v1.setup._ACTION_COOLDOWN_SECONDS", 0.0)
    response = client.post("/api/v1/setup/actions/nope")
    assert response.status_code == 404
    assert response.json()["detail"] == "Setup action not found"
