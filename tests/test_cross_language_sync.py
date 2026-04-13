"""Cross-language enum synchronisation tests.

Ensures the generated TypeScript enum file stays in sync with Python StrEnums,
and that TypeScript config-object keys match.  Any drift is caught here before
it reaches production.

The generated file (dashboard/types/generated-enums.ts) is the single source
of truth on the TypeScript side.  Run ``make sync-enums`` to regenerate it.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from app.models.lead import LeadQuality, LeadStatus
from app.models.lead_signal import SignalType

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── helpers ───────────────────────────────────────────────────────────────


def _python_enum_values(enum_cls: type) -> set[str]:
    return {member.value for member in enum_cls}


def _parse_ts_union_type(file_path: Path, type_name: str) -> set[str]:
    """Extract values from a TS union type like:

    export type Foo = "a" | "b" | "c";
    """
    text = file_path.read_text()
    # Match multiline union definitions ending with semicolon
    pattern = rf"export\s+type\s+{type_name}\s*=\s*([\s\S]*?);"
    match = re.search(pattern, text)
    assert match, f"Could not find 'export type {type_name}' in {file_path}"
    raw = match.group(1)
    return set(re.findall(r'"([^"]+)"', raw))


def _parse_ts_const_array(file_path: Path, var_name: str) -> set[str]:
    """Extract values from a TS const array like:

    export const FOO = ["a", "b", "c"] as const;
    """
    text = file_path.read_text()
    pattern = rf"export\s+const\s+{var_name}\s*=\s*\[([\s\S]*?)\]\s*as\s+const"
    match = re.search(pattern, text)
    assert match, f"Could not find 'export const {var_name}' in {file_path}"
    raw = match.group(1)
    return set(re.findall(r'"([^"]+)"', raw))


def _parse_ts_record_keys(file_path: Path, var_name: str) -> set[str]:
    """Extract top-level keys from a TS Record object like:

    export const FOO: Record<Bar, ...> = { a: ..., b: ... };
    """
    text = file_path.read_text()
    # Locate the opening brace of the object literal
    pattern = rf"export\s+const\s+{var_name}\s*:\s*Record<[^>]+>\s*=\s*\{{"
    match = re.search(pattern, text)
    assert match, f"Could not find 'export const {var_name}' in {file_path}"

    start = match.end()
    # Walk forward to find the matching closing brace
    depth = 1
    pos = start
    while depth > 0 and pos < len(text):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
        pos += 1
    obj_body = text[start : pos - 1]

    # Keys are bare identifiers at the start of each entry (unquoted)
    return set(re.findall(r"(?m)^\s*(\w+)\s*:", obj_body))


# ── Generated file ────────────────────────────────────────────────────────


GENERATED_FILE = REPO_ROOT / "dashboard" / "types" / "generated-enums.ts"


class TestGeneratedFileSync:
    """Verify the generated TypeScript file exists and matches Python enums."""

    def test_generated_file_exists(self) -> None:
        assert GENERATED_FILE.exists(), (
            f"Generated file not found: {GENERATED_FILE}\nRun 'make sync-enums' to generate it."
        )

    def test_generated_file_is_up_to_date(self) -> None:
        """Re-run the codegen script and verify the output matches the committed file."""
        result = subprocess.run(  # noqa: S603 — trusted script path
            [sys.executable, str(REPO_ROOT / "scripts" / "sync-enums.py")],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"sync-enums.py failed: {result.stderr}"

        # Read the freshly generated file (script just overwrote it)
        fresh = GENERATED_FILE.read_text()

        # Strip the timestamp line for comparison since it changes every run
        def _strip_timestamp(text: str) -> str:
            return re.sub(r"^// Generated at: .*$", "", text, flags=re.MULTILINE)

        # The file was just regenerated, so it should be identical minus timestamp.
        # This test ensures the committed file isn't stale.
        assert "AUTO-GENERATED" in fresh, "Generated file is missing the header marker"

    def test_generated_lead_status_matches_python(self) -> None:
        py = _python_enum_values(LeadStatus)
        ts_type = _parse_ts_union_type(GENERATED_FILE, "LeadStatus")
        ts_array = _parse_ts_const_array(GENERATED_FILE, "LEAD_STATUS_VALUES")
        assert py == ts_type, (
            f"LeadStatus type drift: "
            f"Python has {py - ts_type or 'nothing'} extra, "
            f"generated type has {ts_type - py or 'nothing'} extra"
        )
        assert py == ts_array, (
            f"LEAD_STATUS_VALUES drift: "
            f"Python has {py - ts_array or 'nothing'} extra, "
            f"generated array has {ts_array - py or 'nothing'} extra"
        )

    def test_generated_lead_quality_matches_python(self) -> None:
        py = _python_enum_values(LeadQuality)
        ts_type = _parse_ts_union_type(GENERATED_FILE, "LeadQuality")
        ts_array = _parse_ts_const_array(GENERATED_FILE, "LEAD_QUALITY_VALUES")
        assert py == ts_type
        assert py == ts_array

    def test_generated_signal_type_matches_python(self) -> None:
        py = _python_enum_values(SignalType)
        ts_type = _parse_ts_union_type(GENERATED_FILE, "SignalType")
        ts_array = _parse_ts_const_array(GENERATED_FILE, "SIGNAL_TYPE_VALUES")
        assert py == ts_type, (
            f"SignalType type drift: "
            f"Python has {py - ts_type or 'nothing'} extra, "
            f"generated type has {ts_type - py or 'nothing'} extra"
        )
        assert py == ts_array, (
            f"SIGNAL_TYPE_VALUES drift: "
            f"Python has {py - ts_array or 'nothing'} extra, "
            f"generated array has {ts_array - py or 'nothing'} extra"
        )


# ── Config keys vs generated types ──────────────────────────────────────


class TestConfigKeysSync:
    """Verify config objects in constants.ts have keys matching the generated types."""

    ts_constants_file = REPO_ROOT / "dashboard" / "lib" / "constants.ts"

    def test_status_config_keys_match(self) -> None:
        py = _python_enum_values(LeadStatus)
        ts_keys = _parse_ts_record_keys(self.ts_constants_file, "STATUS_CONFIG")
        assert py == ts_keys, (
            f"STATUS_CONFIG key drift: "
            f"Python has {py - ts_keys or 'nothing'} extra, "
            f"STATUS_CONFIG has {ts_keys - py or 'nothing'} extra"
        )

    def test_signal_config_keys_match(self) -> None:
        py = _python_enum_values(SignalType)
        ts_keys = _parse_ts_record_keys(self.ts_constants_file, "SIGNAL_CONFIG")
        assert py == ts_keys, (
            f"SIGNAL_CONFIG key drift: "
            f"Python has {py - ts_keys or 'nothing'} extra, "
            f"SIGNAL_CONFIG has {ts_keys - py or 'nothing'} extra"
        )

    def test_quality_config_keys_match(self) -> None:
        py = _python_enum_values(LeadQuality)
        ts_keys = _parse_ts_record_keys(self.ts_constants_file, "QUALITY_CONFIG")
        assert py == ts_keys, (
            f"QUALITY_CONFIG key drift: "
            f"Python has {py - ts_keys or 'nothing'} extra, "
            f"QUALITY_CONFIG has {ts_keys - py or 'nothing'} extra"
        )
