"""Tests for LLM client JSON parsing."""

from app.llm.client import _extract_json, LLMParseError
import pytest


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
