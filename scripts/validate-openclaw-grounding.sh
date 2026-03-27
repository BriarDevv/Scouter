#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[validate-openclaw-grounding] %s\n' "$*"
}

die() {
  printf '[validate-openclaw-grounding] ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

OPENCLAW_BIN="${OPENCLAW_BIN:-$HOME/.openclaw/bin/openclaw}"
TIMEOUT_SECONDS="${OPENCLAW_GROUNDING_TIMEOUT:-120}"
TOP_LEADS_LIMIT="${OPENCLAW_GROUNDING_TOP_LEADS_LIMIT:-3}"
OUTPUT_DIR="${OPENCLAW_GROUNDING_OUTPUT_DIR:-$(mktemp -d "/tmp/openclaw-grounding-XXXXXX")}"
SESSION_PREFIX="${OPENCLAW_GROUNDING_SESSION_PREFIX:-grounding-$(date '+%Y%m%d-%H%M%S')}"

[[ -x "$OPENCLAW_BIN" ]] || die "No encuentro OpenClaw en $OPENCLAW_BIN"
command -v python3 >/dev/null 2>&1 || die "python3 es requerido"
command -v timeout >/dev/null 2>&1 || die "timeout es requerido"

mkdir -p "$OUTPUT_DIR"
cd "$REPO_ROOT"

log "Usando output dir: $OUTPUT_DIR"

run_wrapper() {
  local name="$1"
  shift
  python3 scripts/clawscoutctl.py "$@" >"$OUTPUT_DIR/$name.wrapper.json"
}

run_openclaw() {
  local name="$1"
  local prompt="$2"
  timeout --foreground "$TIMEOUT_SECONDS" \
    "$OPENCLAW_BIN" agent \
    --agent main \
    --thinking off \
    --session-id "$SESSION_PREFIX-$name" \
    --message "$prompt" \
    --json >"$OUTPUT_DIR/$name.openclaw.raw.json"
}

run_wrapper overview overview
run_wrapper top_leads top-leads --limit "$TOP_LEADS_LIMIT"
run_wrapper recent_drafts recent-drafts --limit "$TOP_LEADS_LIMIT"
run_wrapper settings settings-llm

run_openclaw \
  overview \
  'Use the clawscout-data skill. Run only the overview command. Return only compact JSON with exactly total_leads and drafts_recent_24h copied from the wrapper output. Do not infer or recompute anything.'

run_openclaw \
  top_leads \
  "Use the clawscout-data skill. Run only the top-leads command with limit $TOP_LEADS_LIMIT. Return only compact JSON shaped like {\"top_leads\":[{\"id\":\"...\",\"score\":0.0}]}, preserving order and values from the wrapper output."

run_openclaw \
  recent_drafts \
  "Use the clawscout-data skill. Run only the recent-drafts command with limit $TOP_LEADS_LIMIT. Return only compact JSON shaped like {\"recent_drafts\":[{\"id\":\"...\",\"lead_id\":\"...\",\"status\":\"...\"}]}, preserving order and values from the wrapper output."

run_openclaw \
  settings \
  'Use the clawscout-data skill. Run only the settings-llm command. Return only compact JSON with exactly leader_model, executor_model, reviewer_model, and supported_models copied from the wrapper output.'

python3 - "$OUTPUT_DIR" "$TOP_LEADS_LIMIT" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
top_limit = int(sys.argv[2])


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_openclaw_payload(path: Path):
    outer = load_json(path)
    text = outer["result"]["payloads"][-1]["text"]
    return json.loads(text), outer


overview_wrapper = load_json(output_dir / "overview.wrapper.json")
top_wrapper = load_json(output_dir / "top_leads.wrapper.json")
settings_wrapper = load_json(output_dir / "settings.wrapper.json")

overview_openclaw, overview_outer = load_openclaw_payload(output_dir / "overview.openclaw.raw.json")
top_openclaw, top_outer = load_openclaw_payload(output_dir / "top_leads.openclaw.raw.json")
settings_openclaw, settings_outer = load_openclaw_payload(output_dir / "settings.openclaw.raw.json")

overview_expected = {
    "total_leads": overview_wrapper["data"]["total_leads"],
    "drafts_recent_24h": overview_wrapper["data"]["drafts_recent_24h"],
}
top_expected = [
    {"id": item["id"], "score": item["score"]}
    for item in top_wrapper["data"][:top_limit]
]
recent_drafts_wrapper = load_json(output_dir / "recent_drafts.wrapper.json")
recent_drafts_expected = [
    {"id": item["id"], "lead_id": item["lead_id"], "status": item["status"]}
    for item in recent_drafts_wrapper["data"][:top_limit]
]
settings_expected = {
    "leader_model": settings_wrapper["data"]["leader_model"],
    "executor_model": settings_wrapper["data"]["executor_model"],
    "reviewer_model": settings_wrapper["data"]["reviewer_model"],
    "supported_models": settings_wrapper["data"]["supported_models"],
}

recent_drafts_openclaw, recent_drafts_outer = load_openclaw_payload(output_dir / "recent_drafts.openclaw.raw.json")
top_openclaw = top_openclaw["top_leads"]
recent_drafts_openclaw = recent_drafts_openclaw["recent_drafts"]

comparisons = [
    ("overview", overview_expected, overview_openclaw),
    ("top_leads", top_expected, top_openclaw),
    ("recent_drafts", recent_drafts_expected, recent_drafts_openclaw),
    ("settings", settings_expected, settings_openclaw),
]

for name, expected, actual in comparisons:
    if expected != actual:
        print(f"{name}: mismatch", file=sys.stderr)
        print("expected:", json.dumps(expected, indent=2, sort_keys=True), file=sys.stderr)
        print("actual:", json.dumps(actual, indent=2, sort_keys=True), file=sys.stderr)
        sys.exit(1)

report = {
    "ok": True,
    "overview": overview_expected,
    "top_leads": top_expected,
    "recent_drafts": recent_drafts_expected,
    "settings": settings_expected,
    "session_keys": {
        "overview": overview_outer["result"]["meta"]["agentMeta"]["sessionId"],
        "top_leads": top_outer["result"]["meta"]["agentMeta"]["sessionId"],
        "recent_drafts": recent_drafts_outer["result"]["meta"]["agentMeta"]["sessionId"],
        "settings": settings_outer["result"]["meta"]["agentMeta"]["sessionId"],
    },
    "models": {
        "overview": overview_outer["result"]["meta"]["agentMeta"]["model"],
        "top_leads": top_outer["result"]["meta"]["agentMeta"]["model"],
        "recent_drafts": recent_drafts_outer["result"]["meta"]["agentMeta"]["model"],
        "settings": settings_outer["result"]["meta"]["agentMeta"]["model"],
    },
}

(output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
PY

log "Validacion completada. Evidencia en $OUTPUT_DIR"
