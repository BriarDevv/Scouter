import re
from pathlib import Path

import sqlalchemy as sa


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
    types_dir = Path("dashboard/types")
    all_type_content = "\n".join(p.read_text(encoding="utf-8") for p in types_dir.glob("*.ts"))

    for expected in (
        "website_error",
        "classifying",
    ):
        assert expected in all_type_content


def test_services_domain_packages_do_not_cross_import_each_other():
    root = Path("app/services")
    domain_dirs = {
        path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith("__")
    }
    violations: set[str] = set()
    baseline_allowed = {
        "app/services/pipeline/batch_review_service.py: imports settings",
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
        "app/services/dashboard/ai_office_service.py: imports comms",
        "app/services/outreach/generator.py: imports settings",
        "app/services/settings/setup_service.py: imports dashboard",
    }

    for domain in sorted(domain_dirs):
        for path in (root / domain).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for other in sorted(domain_dirs - {domain}):
                token = f"app.services.{other}."
                if token in text:
                    violations.add(f"{path}: imports {other}")

    assert violations - baseline_allowed == set()


def test_models_do_not_import_from_llm_layer():
    """Models should not depend on the LLM layer (except via re-exports)."""
    violations: list[str] = []
    for path in Path("app/models").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from app.llm." in text:
            violations.append(str(path))
    assert violations == [], f"Models import from app.llm: {violations}"


def test_core_does_not_import_from_services_or_workers():
    """Core utilities must not depend on services or workers."""
    violations: list[str] = []
    for path in Path("app/core").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for layer in ("app.services.", "app.workers."):
            if layer in text:
                violations.append(f"{path}: imports {layer}")
    assert violations == [], f"Core imports from upper layers: {violations}"


def test_core_does_not_import_from_llm():
    """Core must not import from app.llm (dependency direction violation)."""
    violations: list[str] = []
    for path in Path("app/core").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from app.llm." in text:
            violations.append(str(path))
    assert violations == [], f"Core imports from app.llm: {violations}"


def test_service_packages_have_explicit_exports():
    """Each service sub-package should define its public API in __init__.py."""
    root = Path("app/services")
    missing: list[str] = []
    for path in root.iterdir():
        if not path.is_dir() or path.name.startswith("__"):
            continue
        init = path / "__init__.py"
        if not init.exists():
            missing.append(f"{path.name}: no __init__.py")
            continue
        text = init.read_text(encoding="utf-8")
        if "__all__" not in text and "import" not in text:
            missing.append(f"{path.name}: empty __init__.py (no exports)")
    assert missing == [], f"Service packages without explicit exports: {missing}"


def test_no_hardcoded_absolute_paths_in_commands():
    """Claude Code commands should not contain hardcoded absolute home paths."""
    violations: list[str] = []
    for path in Path(".claude/commands").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "/home/" in text and "cd /home/" in text:
            violations.append(str(path))
    assert violations == [], f"Commands with hardcoded paths: {violations}"


def test_no_hardcoded_absolute_paths_in_skills():
    """Skills should not contain hardcoded absolute home paths."""
    violations: list[str] = []
    for path in Path("skills").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "/home/" in text and "cd /home/" in text:
            violations.append(str(path))
    assert violations == [], f"Skills with hardcoded paths: {violations}"


def test_conftest_uses_postgresql():
    """Guardrail: tests must run against PostgreSQL via testcontainers."""
    conftest = Path("tests/conftest.py").read_text(encoding="utf-8")
    assert "testcontainers" in conftest, (
        "conftest.py must use PostgreSQL via testcontainers to match production."
    )


def test_alembic_migrations_apply_cleanly():
    """Verify all Alembic migrations apply to a fresh PostgreSQL database."""
    import os

    from alembic.config import Config
    from sqlalchemy import create_engine as sa_create_engine
    from sqlalchemy import inspect as sa_inspect

    from alembic import command

    db_url = os.environ["DATABASE_URL"]
    fresh_engine = sa_create_engine(db_url)

    # Drop all tables first to test migrations from scratch
    from app.db.base import Base

    Base.metadata.drop_all(bind=fresh_engine)

    # Also drop alembic_version table if it exists
    with fresh_engine.connect() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        # Drop all enum types that might linger
        for enum_name in [
            "leadstatus",
            "signaltype",
            "draftstatus",
            "outboundstatus",
            "outboundchannel",
            "messagedirection",
            "communicationchannel",
        ]:
            conn.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
        conn.commit()

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    inspector = sa_inspect(fresh_engine)
    tables = set(inspector.get_table_names())
    assert "leads" in tables, "leads table must exist after migrations"
    assert "pipeline_runs" in tables, "pipeline_runs table must exist after migrations"
    assert "llm_invocations" in tables, "llm_invocations table must exist after migrations"
    assert "operational_settings" in tables, (
        "operational_settings table must exist after migrations"
    )

    # Restore tables via create_all for remaining tests
    Base.metadata.drop_all(bind=fresh_engine)
    with fresh_engine.connect() as conn:
        conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        for enum_name in [
            "leadstatus",
            "signaltype",
            "draftstatus",
            "outboundstatus",
            "outboundchannel",
            "messagedirection",
            "communicationchannel",
        ]:
            conn.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
        conn.commit()
    Base.metadata.create_all(bind=fresh_engine)
    fresh_engine.dispose()
