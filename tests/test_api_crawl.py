"""Tests for the Google Maps API key endpoint contract.

The key used to be deploy-managed (env-only, 409 on any PATCH). It is now
DB-first with env fallback: operators can load/rotate/clear it from the
UI, and the env var is still honored when the DB row is empty.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.v1.crawl import ApiKeyUpdate, api_key_status, delete_api_key, update_api_key
from app.services.deploy_config_service import get_effective_google_maps_key


def test_status_reports_env_when_db_empty_and_env_set(db: Session, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.GOOGLE_MAPS_API_KEY", "AIzaSy1234567890abcdefghijklmnop"
    )

    payload = api_key_status(db)

    assert payload["configured"] is True
    assert payload["masked"] == "...mnop"
    assert payload["managed_by"] == "env"
    assert payload["source"] == "env"
    assert payload["mutable_via_api"] is True


def test_status_reports_none_when_both_sources_empty(db: Session, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", None)

    payload = api_key_status(db)

    assert payload["configured"] is False
    assert payload["managed_by"] == "none"
    assert payload["source"] is None
    assert payload["mutable_via_api"] is True


def test_patch_persists_valid_key_and_db_wins_over_env(db: Session, monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.GOOGLE_MAPS_API_KEY", "AIzaEnvFallback123456789012345678"
    )

    update_api_key(ApiKeyUpdate(api_key="AIzaDBKey1234567890abcdefghijklmn"), db)

    # DB should take precedence over env
    effective = get_effective_google_maps_key(db)
    assert effective == "AIzaDBKey1234567890abcdefghijklmn"

    status = api_key_status(db)
    assert status["configured"] is True
    assert status["source"] == "db"
    assert status["masked"] == "...klmn"


def test_patch_rejects_key_without_aiza_prefix(db: Session):  # noqa: N802
    with pytest.raises(HTTPException) as exc_info:
        update_api_key(ApiKeyUpdate(api_key="wrong-prefix-but-long-enough-to-pass-len-check"), db)

    assert exc_info.value.status_code == 422
    assert "AIza" in str(exc_info.value.detail)


def test_patch_rejects_too_short_key(db: Session):
    with pytest.raises(HTTPException) as exc_info:
        update_api_key(ApiKeyUpdate(api_key="AIzaShort"), db)

    assert exc_info.value.status_code == 422


def test_delete_clears_db_row_and_falls_back_to_env(db: Session, monkeypatch):
    # Seed DB with a valid key first.
    update_api_key(ApiKeyUpdate(api_key="AIzaDBKey1234567890abcdefghijklmn"), db)
    # Now configure an env fallback and clear the DB row.
    monkeypatch.setattr(
        "app.core.config.settings.GOOGLE_MAPS_API_KEY", "AIzaEnv1234567890abcdefghijklmnop"
    )

    delete_api_key(db)

    effective = get_effective_google_maps_key(db)
    assert effective == "AIzaEnv1234567890abcdefghijklmnop"
    status = api_key_status(db)
    assert status["source"] == "env"
