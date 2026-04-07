"""Tests for agent core — tool registry, hermes format parsing, prompt building, events."""

import uuid

import pytest

# ── Tool Registry ──────────────────────────────────────────


def test_tool_registry_loads_50_tools():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    assert len(registry.list_all()) >= 50


def test_tool_registry_all_handlers_callable():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    for tool in registry.list_all():
        assert callable(tool.handler), f"{tool.name} handler not callable"


def test_tool_registry_schema_is_cached():
    from app.agent.core import _cached_tools_schema

    s1 = _cached_tools_schema()
    s2 = _cached_tools_schema()
    assert s1 is s2


def test_tool_registry_schema_contains_all_tools():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    schema = registry.to_hermes_schema()
    tool_count = len(registry.list_all())
    assert schema.count("<tool>") == tool_count


def test_tool_registry_validates_required_param():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    with pytest.raises(ValueError, match="obligatorio"):
        registry.validate_call("update_lead_status", {})


def test_tool_registry_validates_enum_param():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    with pytest.raises(ValueError, match="debe ser uno de"):
        registry.validate_call("update_lead_status", {"lead_id": "abc", "status": "invalid"})


def test_tool_registry_coerces_types():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    result = registry.validate_call("search_leads", {"limit": "5"})
    assert isinstance(result["limit"], int)
    assert result["limit"] == 5


def test_tool_registry_unknown_tool_raises():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    with pytest.raises(KeyError, match="nonexistent"):
        registry.validate_call("nonexistent", {})


# ── Hermes Format Parsing ──────────────────────────────────


def test_hermes_parse_single_tool_call():
    from app.agent.hermes_format import parse_tool_calls

    text = '<tool_call>\n{"name": "health_check", "arguments": {}}\n</tool_call>'
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "health_check"


def test_hermes_parse_multiple_tool_calls():
    from app.agent.hermes_format import parse_tool_calls

    text = (
        '<tool_call>{"name": "health_check", "arguments": {}}</tool_call>'
        "\n"
        '<tool_call>{"name": "get_current_time", "arguments": {}}</tool_call>'
    )
    calls = parse_tool_calls(text)
    assert len(calls) == 2
    assert calls[0].name == "health_check"
    assert calls[1].name == "get_current_time"


def test_hermes_parse_parameters_key():
    from app.agent.hermes_format import parse_tool_calls

    text = '<tool_call>{"name": "search_leads", "parameters": {"limit": 5}}</tool_call>'
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].arguments == {"limit": 5}


def test_hermes_parse_malformed_json_returns_empty():
    from app.agent.hermes_format import parse_tool_calls

    text = "<tool_call>not json</tool_call>"
    calls = parse_tool_calls(text)
    assert len(calls) == 0


def test_hermes_parse_no_tool_calls():
    from app.agent.hermes_format import parse_tool_calls

    calls = parse_tool_calls("Just normal text with no tools")
    assert len(calls) == 0


def test_hermes_contains_tool_call():
    from app.agent.hermes_format import contains_tool_call

    assert contains_tool_call("<tool_call>test</tool_call>") is True
    assert contains_tool_call("normal text") is False


def test_hermes_format_tool_result():
    from app.agent.hermes_format import format_tool_result

    result = format_tool_result("health_check", {"status": "ok"})
    assert "<tool_response>" in result
    assert "health_check" in result
    assert "ok" in result


def test_hermes_format_tool_result_with_error():
    from app.agent.hermes_format import format_tool_result

    result = format_tool_result("test", None, error="something failed")
    assert "something failed" in result


# ── Agent Prompts ──────────────────────────────────────────


def test_agent_prompt_includes_personality():
    from app.agent.prompts import build_agent_system_prompt

    prompt = build_agent_system_prompt("<tools></tools>")
    assert "Mote" in prompt
    assert "rioplatense" in prompt


def test_agent_prompt_includes_context():
    from app.agent.prompts import build_agent_system_prompt

    prompt = build_agent_system_prompt("<tools></tools>", system_context="Total leads: 100")
    assert "Total leads: 100" in prompt


def test_agent_prompt_includes_security():
    from app.agent.prompts import build_agent_system_prompt

    prompt = build_agent_system_prompt("<tools></tools>")
    assert "credenciales" in prompt.lower() or "SEGURIDAD" in prompt


# ── Agent Events ───────────────────────────────────────────


def test_agent_events_are_frozen():
    from app.agent.events import TextDelta

    td = TextDelta(content="hello")
    with pytest.raises(AttributeError):
        td.content = "changed"


def test_agent_event_types_exist():
    from app.agent.events import (
        AgentError,
        TextDelta,
        ToolStart,
        TurnComplete,
    )

    assert TextDelta(content="x").content == "x"
    assert ToolStart(tool_name="t", tool_call_id="1", arguments={}).tool_name == "t"
    assert AgentError(error="e").error == "e"
    assert TurnComplete(message_id=uuid.uuid4()).message_id is not None


# ── Tool Execution ─────────────────────────────────────────


def test_execute_tool_unknown_returns_error():
    from unittest.mock import MagicMock

    import app.agent.tools  # noqa: F401
    from app.agent.core import _execute_tool

    result, error = _execute_tool(MagicMock(), "nonexistent_tool", {})
    assert result is None
    assert "no existe" in error


def test_execute_tool_suggests_similar():
    import app.agent.tools  # noqa: F401
    from app.agent.core import _suggest_tools

    suggestions = _suggest_tools("get_leads")
    assert "list_top_leads" in suggestions or "search_leads" in suggestions


def test_execute_tool_get_current_time():
    from unittest.mock import MagicMock

    import app.agent.tools  # noqa: F401
    from app.agent.core import _execute_tool

    result, error = _execute_tool(MagicMock(), "get_current_time", {})
    assert error is None
    assert "datetime" in result
    assert "date" in result


# ── takes_db auto-detection ────────────────────────────────


def test_tool_takes_db_auto_detected():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    tool = registry.get("generate_draft")
    assert tool is not None, "generate_draft not found in registry"
    assert tool.takes_db is True


def test_tool_without_db_has_takes_db_false():
    import app.agent.tools  # noqa: F401
    from app.agent.tool_registry import registry

    tool = registry.get("get_current_time")
    assert tool is not None, "get_current_time not found in registry"
    assert tool.takes_db is False
