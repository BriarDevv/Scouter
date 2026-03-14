"""Tests for AI workspace configuration file management."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.ai_workspace_service import (
    DEFAULT_TEMPLATES,
    EDITABLE_KEYS,
    WORKSPACE_FILES,
    get_file_content,
    get_skills_status,
    get_workspace_status,
    reset_file_to_template,
    update_file_content,
    validate_file_structure,
)


@pytest.fixture()
def workspace(tmp_path):
    """Create a temporary workspace with sample files and patch the root."""
    # Create workspace files
    (tmp_path / "AGENTS.md").write_text(
        "# AGENTS.md\n\n## Session Startup\n\nDo the thing.\n"
    )
    (tmp_path / "SOUL.md").write_text(
        "# SOUL.md\n\n## Core Truths\n\nBe helpful.\n"
    )
    (tmp_path / "IDENTITY.md").write_text(
        "# IDENTITY.md\n\n- **Name:** TestBot\n"
    )
    (tmp_path / "HEARTBEAT.md").write_text(
        "# HEARTBEAT.md\n\n# Nothing here yet.\n"
    )
    (tmp_path / "TOOLS.md").write_text(
        "# TOOLS.md\n\n## SSH Hosts\n\n- server1\n"
    )
    (tmp_path / "USER.md").write_text(
        "# USER.md\n\n- **Name:** Mateo\n"
    )

    # Create skills directory with a sample skill
    skill_dir = tmp_path / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        '---\nname: my-skill\ndescription: "A test skill"\n---\n\nSkill body.\n'
    )

    # Create a second skill directory without SKILL.md
    (tmp_path / "skills" / "empty-skill").mkdir(parents=True)

    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        yield tmp_path


# ── get_workspace_status ──────────────────────────────────────────────


def test_get_workspace_status(workspace):
    result = get_workspace_status()

    assert "files" in result
    assert "skills" in result
    assert "models" in result
    assert "workspace_path" in result
    assert "openclaw_installed" in result
    assert "onboarding_completed" in result

    # All 6 workspace files should be present
    keys = [f["key"] for f in result["files"]]
    assert set(keys) == set(WORKSPACE_FILES.keys())

    # Each file should exist in our temp workspace
    for f in result["files"]:
        assert f["exists"] is True
        assert f["size_bytes"] is not None
        assert f["size_bytes"] > 0
        assert f["last_modified"] is not None
        assert f["is_empty"] is False
        assert f["preview"] is not None

    # agents should not be editable
    agents = next(f for f in result["files"] if f["key"] == "agents")
    assert agents["editable"] is False

    # soul should be editable
    soul = next(f for f in result["files"] if f["key"] == "soul")
    assert soul["editable"] is True
    assert soul["has_valid_structure"] is True

    # workspace_path should point to tmp
    assert result["workspace_path"] == str(workspace)


# ── get_file_content ──────────────────────────────────────────────────


def test_get_file_content_existing(workspace):
    result = get_file_content("soul")
    assert result["key"] == "soul"
    assert result["filename"] == "SOUL.md"
    assert result["exists"] is True
    assert "Core Truths" in result["content"]


def test_get_file_content_nonexistent(workspace):
    # Remove the file to simulate missing
    (workspace / "TOOLS.md").unlink()
    result = get_file_content("tools")
    assert result["key"] == "tools"
    assert result["exists"] is False
    assert result["content"] is None


def test_get_file_content_unknown_key(workspace):
    with pytest.raises(ValueError, match="Unknown workspace file key"):
        get_file_content("nonexistent")


# ── update_file_content ──────────────────────────────────────────────


def test_update_file_content(workspace):
    new_content = "# Updated SOUL\n\n## Core Truths\n\nNew content.\n"
    result = update_file_content("soul", new_content)
    assert result["key"] == "soul"
    assert result["exists"] is True
    assert result["content"] == new_content
    assert result["updated"] is True

    # Verify file was actually written
    actual = (workspace / "SOUL.md").read_text()
    assert actual == new_content


def test_update_agents_rejected(workspace):
    with pytest.raises(PermissionError, match="not editable"):
        update_file_content("agents", "# Hacked agents")


def test_update_unknown_key_rejected(workspace):
    with pytest.raises(ValueError, match="Unknown workspace file key"):
        update_file_content("badkey", "content")


# ── reset_file_to_template ───────────────────────────────────────────


def test_reset_file_to_template(workspace):
    # First overwrite the file
    (workspace / "USER.md").write_text("garbage")

    result = reset_file_to_template("user")
    assert result["key"] == "user"
    assert result["exists"] is True
    assert result["reset"] is True
    assert result["content"] == DEFAULT_TEMPLATES["user"]

    # Verify file was actually written
    actual = (workspace / "USER.md").read_text()
    assert actual == DEFAULT_TEMPLATES["user"]


def test_reset_agents_rejected(workspace):
    with pytest.raises(PermissionError, match="not editable"):
        reset_file_to_template("agents")


# ── validate_file_structure ──────────────────────────────────────────


def test_validate_structure_empty_file(workspace):
    warnings = validate_file_structure("soul", "")
    assert "File is empty" in warnings


def test_validate_structure_whitespace_only(workspace):
    warnings = validate_file_structure("soul", "   \n\n  ")
    assert "File is empty" in warnings


def test_validate_structure_missing_section(workspace):
    warnings = validate_file_structure("soul", "# SOUL.md\n\nNo core truths here.\n")
    assert "Missing required section: Core Truths" in warnings


def test_validate_structure_valid(workspace):
    warnings = validate_file_structure("soul", "# SOUL.md\n\n## Core Truths\n\nGood.\n")
    assert warnings == []


def test_validate_structure_identity_missing_name(workspace):
    warnings = validate_file_structure("identity", "# IDENTITY.md\n\nNo fields.\n")
    assert "Missing required field: Name" in warnings


def test_validate_structure_identity_valid(workspace):
    warnings = validate_file_structure("identity", "# IDENTITY.md\n\nName: Bot\n")
    assert warnings == []


def test_validate_structure_no_checks_key(workspace):
    """Keys without specific checks should return empty warnings for non-empty content."""
    warnings = validate_file_structure("tools", "# TOOLS.md\n\nSomething.\n")
    assert warnings == []


# ── skills detection ─────────────────────────────────────────────────


def test_skills_detection(workspace):
    skills = get_skills_status()
    assert len(skills) == 2

    # Find the skill with SKILL.md
    real_skill = next(s for s in skills if s["name"] == "my-skill")
    assert real_skill["exists"] is True
    assert real_skill["description"] == "A test skill"

    # Find the skill without SKILL.md
    empty_skill = next(s for s in skills if s["name"] == "empty-skill")
    assert empty_skill["exists"] is False
    assert empty_skill["description"] is None


def test_skills_detection_no_skills_dir(workspace):
    """When skills/ doesn't exist, return empty list."""
    import shutil
    shutil.rmtree(workspace / "skills")
    skills = get_skills_status()
    assert skills == []


# ── API endpoint tests ───────────────────────────────────────────────


def test_api_get_workspace_status(client, tmp_path):
    """GET /api/v1/settings/ai-workspace returns workspace status."""
    # Create minimal workspace
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\n\n## Session Startup\n")
    (tmp_path / "SOUL.md").write_text("# SOUL.md\n\n## Core Truths\n")
    (tmp_path / "IDENTITY.md").write_text("# IDENTITY.md\n\nName: X\n")
    (tmp_path / "HEARTBEAT.md").write_text("# HEARTBEAT.md\n")
    (tmp_path / "TOOLS.md").write_text("# TOOLS.md\n")
    (tmp_path / "USER.md").write_text("# USER.md\n")

    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.get("/api/v1/settings/ai-workspace")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["files"]) == 6
    assert isinstance(data["skills"], list)
    assert "leader" in data["models"]
    assert isinstance(data["openclaw_installed"], bool)
    assert isinstance(data["onboarding_completed"], bool)


def test_api_get_file_content(client, tmp_path):
    """GET /api/v1/settings/ai-workspace/soul returns file content."""
    (tmp_path / "SOUL.md").write_text("# My Soul\n\n## Core Truths\n")

    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.get("/api/v1/settings/ai-workspace/soul")

    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "soul"
    assert data["exists"] is True
    assert "My Soul" in data["content"]


def test_api_get_agents_rejected(client, tmp_path):
    """GET /api/v1/settings/ai-workspace/agents returns 403."""
    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.get("/api/v1/settings/ai-workspace/agents")
    assert resp.status_code == 403


def test_api_get_unknown_key(client, tmp_path):
    """GET /api/v1/settings/ai-workspace/bogus returns 404."""
    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.get("/api/v1/settings/ai-workspace/bogus")
    assert resp.status_code == 404


def test_api_put_file_content(client, tmp_path):
    """PUT /api/v1/settings/ai-workspace/soul writes content."""
    (tmp_path / "SOUL.md").write_text("old content")

    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.put(
            "/api/v1/settings/ai-workspace/soul",
            json={"content": "# New Soul\n\n## Core Truths\n"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["exists"] is True
    assert "New Soul" in data["content"]


def test_api_put_agents_rejected(client, tmp_path):
    """PUT /api/v1/settings/ai-workspace/agents returns 403."""
    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.put(
            "/api/v1/settings/ai-workspace/agents",
            json={"content": "hacked"},
        )
    assert resp.status_code == 403


def test_api_reset_file(client, tmp_path):
    """POST /api/v1/settings/ai-workspace/user/reset restores template."""
    (tmp_path / "USER.md").write_text("garbage")

    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.post("/api/v1/settings/ai-workspace/user/reset")

    assert resp.status_code == 200
    data = resp.json()
    assert data["reset"] is True
    assert data["key"] == "user"
    assert data["content"] == DEFAULT_TEMPLATES["user"]


def test_api_reset_agents_rejected(client, tmp_path):
    """POST /api/v1/settings/ai-workspace/agents/reset returns 403."""
    with patch(
        "app.services.ai_workspace_service._workspace_root",
        return_value=tmp_path,
    ):
        resp = client.post("/api/v1/settings/ai-workspace/agents/reset")
    assert resp.status_code == 403
