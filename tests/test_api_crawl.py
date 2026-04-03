import pytest
from fastapi import HTTPException

from app.api.v1.crawl import ApiKeyUpdate, api_key_status, update_api_key


def test_google_maps_api_key_status_is_deploy_managed(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "AIzaSy1234567890")

    payload = api_key_status()

    assert payload["configured"] is True
    assert payload["masked"] == "...7890"
    assert payload["managed_by"] == "env"
    assert payload["mutable_via_api"] is False


def test_google_maps_api_key_cannot_be_mutated_via_http():
    with pytest.raises(HTTPException) as exc_info:
        update_api_key(ApiKeyUpdate(api_key="AIzaSy1234567890"))

    payload = exc_info.value.detail
    assert exc_info.value.status_code == 409
    assert payload["managed_by"] == "env"
    assert payload["mutable_via_api"] is False
    assert "no puede modificarse desde HTTP" in payload["message"]
