import re
from pathlib import Path


def test_http_layer_does_not_mutate_dotenv_files():
    violations: list[str] = []

    for path in Path("app/api").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if ".env" not in text:
            continue
        if "write_text(" in text or "os.environ[" in text:
            violations.append(str(path))

    assert violations == []


def test_no_private_llm_helper_imports_outside_llm():
    violations: list[str] = []
    patterns = (
        "_call_ollama_chat",
        "_extract_json",
    )

    for path in Path("app").rglob("*.py"):
        if str(path).startswith("app/llm/"):
            continue
        text = path.read_text(encoding="utf-8")
        if any(pattern in text for pattern in patterns):
            violations.append(str(path))

    assert violations == []


def test_no_direct_redis_writes_in_api_layer():
    violations: list[str] = []
    write_patterns = (
        ".set(",
        ".delete(",
        ".setex(",
        ".expire(",
    )

    for path in Path("app/api").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "redis" not in text.lower():
            continue
        if any(pattern in text for pattern in write_patterns):
            violations.append(str(path))

    assert violations == []


def test_all_worker_tasks_use_shared_celery_app():
    violations: list[str] = []

    for path in Path("app/workers").rglob("*.py"):
        if path.name == "celery_app.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bCelery\s*\(", text):
            violations.append(str(path))

    assert violations == []


def test_no_manual_enum_drift_in_frontend_for_known_backend_values():
    frontend_types = Path("dashboard/types/index.ts").read_text(encoding="utf-8")

    for expected in (
        "website_error",
        "classifying",
    ):
        assert expected in frontend_types


def test_services_domain_packages_do_not_cross_import_each_other():
    root = Path("app/services")
    domain_dirs = {
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }
    violations: set[str] = set()
    baseline_allowed = {
        "app/services/comms/whatsapp_actions.py: imports notifications",
        "app/services/comms/whatsapp_actions.py: imports outreach",
        "app/services/inbox/inbound_mail_service.py: imports notifications",
        "app/services/inbox/inbound_mail_service.py: imports settings",
        "app/services/inbox/reply_classification_service.py: imports notifications",
        "app/services/inbox/reply_classification_service.py: imports settings",
        "app/services/inbox/reply_draft_review_service.py: imports settings",
        "app/services/inbox/reply_response_service.py: imports settings",
        "app/services/inbox/reply_send_service.py: imports notifications",
        "app/services/inbox/reply_send_service.py: imports outreach",
        "app/services/leads/scoring_service.py: imports notifications",
        "app/services/notifications/notification_emitter.py: imports settings",
        "app/services/notifications/notification_service.py: imports comms",
        "app/services/notifications/notification_service.py: imports settings",
        "app/services/outreach/mail_service.py: imports notifications",
        "app/services/outreach/mail_service.py: imports settings",
        "app/services/outreach/auto_send_service.py: imports comms",
        "app/services/outreach/auto_send_service.py: imports notifications",
        "app/services/outreach/outreach_service.py: imports comms",
        "app/services/outreach/outreach_service.py: imports leads",
        "app/services/leads/lead_service.py: imports pipeline",
        "app/services/research/brief_service.py: imports notifications",
        "app/services/research/brief_service.py: imports settings",
        "app/services/settings/settings_service.py: imports inbox",
        "app/services/settings/settings_service.py: imports outreach",
        "app/services/settings/setup_status_service.py: imports outreach",
    }

    for domain in sorted(domain_dirs):
        for path in (root / domain).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for other in sorted(domain_dirs - {domain}):
                token = f"app.services.{other}."
                if token in text:
                    violations.add(f"{path}: imports {other}")

    assert violations - baseline_allowed == set()
