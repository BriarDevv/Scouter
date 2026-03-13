"""Tests for LLM client parsing and role-based model resolution."""

import httpx
import pytest

from app.llm.client import (
    LLMParseError,
    _call_ollama,
    _extract_json,
    evaluate_lead_quality,
    generate_outreach_draft,
    summarize_business,
)
from app.llm.roles import LLMRole


def test_extract_json_direct():
    result = _extract_json('{"summary": "A cafe in CABA"}')
    assert result["summary"] == "A cafe in CABA"


def test_extract_json_from_markdown():
    raw = '```json\n{"summary": "Test business"}\n```'
    result = _extract_json(raw)
    assert result["summary"] == "Test business"


def test_extract_json_with_surrounding_text():
    raw = 'Here is the result:\n{"quality": "high", "reasoning": "Good prospect"}\nDone.'
    result = _extract_json(raw)
    assert result["quality"] == "high"


def test_extract_json_fails_gracefully():
    with pytest.raises(LLMParseError):
        _extract_json("This is not JSON at all")


def test_extract_json_nested():
    raw = '{"subject": "Hola", "body": "Test with \\"quotes\\" inside"}'
    result = _extract_json(raw)
    assert result["subject"] == "Hola"


def test_call_ollama_resolves_model_from_role(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": '{"summary": "ok"}'}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr("app.llm.client.resolve_model_for_role", lambda role: "qwen3.5:4b")
    monkeypatch.setattr(httpx, "Client", FakeClient)

    raw = _call_ollama("hello", role=LLMRole.LEADER)

    assert raw == '{"summary": "ok"}'
    assert captured["payload"]["model"] == "qwen3.5:4b"
    assert captured["payload"]["prompt"] == "hello"


def test_summarize_business_forwards_explicit_role(monkeypatch):
    captured = {}

    def fake_call(prompt, role=LLMRole.EXECUTOR):
        captured["role"] = role
        return '{"summary": "Role-aware summary"}'

    monkeypatch.setattr("app.llm.client._call_ollama", fake_call)

    summary = summarize_business(
        business_name="Cafe Test",
        industry="Cafe",
        city="CABA",
        website_url="https://example.com",
        instagram_url=None,
        signals=[],
        role=LLMRole.LEADER,
    )

    assert summary == "Role-aware summary"
    assert captured["role"] == LLMRole.LEADER


def test_public_helpers_default_to_executor_role(monkeypatch):
    captured = []
    responses = iter(
        [
            '{"quality": "medium", "reasoning": "Solid fit", "suggested_angle": "SEO"}',
            '{"subject": "Hola", "body": "Mensaje"}',
        ]
    )

    def fake_call(prompt, role=LLMRole.EXECUTOR):
        captured.append(role)
        return next(responses)

    monkeypatch.setattr("app.llm.client._call_ollama", fake_call)

    evaluation = evaluate_lead_quality(
        business_name="Cafe Test",
        industry="Cafe",
        city="CABA",
        website_url="https://example.com",
        instagram_url=None,
        signals=[],
        score=42,
    )
    draft = generate_outreach_draft(
        business_name="Cafe Test",
        industry="Cafe",
        city="CABA",
        website_url="https://example.com",
        instagram_url=None,
        llm_summary="Summary",
        llm_suggested_angle="SEO",
        signals=[],
    )

    assert captured == [LLMRole.EXECUTOR, LLMRole.EXECUTOR]
    assert evaluation["quality"] == "medium"
    assert draft["subject"] == "Hola"
