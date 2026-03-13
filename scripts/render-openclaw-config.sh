#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[render-openclaw-config] %s\n' "$*"
}

warn() {
  printf '[render-openclaw-config] WARN: %s\n' "$*" >&2
}

die() {
  printf '[render-openclaw-config] ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

TEMPLATE_PATH="${OPENCLAW_TEMPLATE_PATH:-$REPO_ROOT/infra/openclaw/openclaw.template.json}"
CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
CONFIG_DIR="$(dirname -- "$CONFIG_PATH")"
WORKSPACE_PATH="${OPENCLAW_WORKSPACE:-$REPO_ROOT}"
OPENCLAW_TIMEOUT_SECONDS="${OPENCLAW_TIMEOUT_SECONDS:-180}"

LEADER_MODEL_ID="${OPENCLAW_LEADER_MODEL:-qwen3.5:4b}"
EXECUTOR_MODEL_ID="${OPENCLAW_EXECUTOR_MODEL:-qwen3.5:9b}"
REVIEWER_MODEL_ID="${OPENCLAW_REVIEWER_MODEL:-qwen3.5:27b}"

OLLAMA_SCHEME="${OPENCLAW_OLLAMA_SCHEME:-http}"
OLLAMA_PORT="${OPENCLAW_OLLAMA_PORT:-11435}"
OLLAMA_HOST_OVERRIDE="${OPENCLAW_OLLAMA_HOST:-}"
OLLAMA_BASE_URL_OVERRIDE="${OPENCLAW_OLLAMA_BASE_URL:-${OLLAMA_BASE_URL:-}}"

resolve_windows_host_from_wsl() {
  local gateway
  gateway="$(ip route show default 2>/dev/null | awk '/default/ { print $3; exit }')"
  [[ -n "$gateway" ]] || return 1
  printf '%s' "$gateway"
}

resolve_ollama_base_url() {
  local host
  if [[ -n "$OLLAMA_BASE_URL_OVERRIDE" ]]; then
    printf '%s' "$OLLAMA_BASE_URL_OVERRIDE"
    return 0
  fi

  if [[ -n "$OLLAMA_HOST_OVERRIDE" ]]; then
    host="$OLLAMA_HOST_OVERRIDE"
  else
    host="$(resolve_windows_host_from_wsl || true)"
  fi

  [[ -n "$host" ]] || die "No pude resolver el host de Ollama. Definí OPENCLAW_OLLAMA_BASE_URL o OPENCLAW_OLLAMA_HOST."
  printf '%s://%s:%s' "$OLLAMA_SCHEME" "$host" "$OLLAMA_PORT"
}

[[ -f "$TEMPLATE_PATH" ]] || die "No existe la plantilla: $TEMPLATE_PATH"
mkdir -p "$CONFIG_DIR"

OLLAMA_BASE_URL_RENDERED="$(resolve_ollama_base_url)"
TMP_PATH="$(mktemp "$CONFIG_DIR/openclaw.json.tmp.XXXXXX")"

export TEMPLATE_PATH
export CONFIG_PATH
export TMP_PATH
export WORKSPACE_PATH
export OLLAMA_BASE_URL_RENDERED
export LEADER_MODEL_ID
export EXECUTOR_MODEL_ID
export REVIEWER_MODEL_ID
export OPENCLAW_TIMEOUT_SECONDS

python3 - <<'PY'
import json
import os
import pathlib
import sys

template_path = pathlib.Path(os.environ["TEMPLATE_PATH"])
config_path = pathlib.Path(os.environ["CONFIG_PATH"])
tmp_path = pathlib.Path(os.environ["TMP_PATH"])

placeholders = {
    "__OLLAMA_BASE_URL__": os.environ["OLLAMA_BASE_URL_RENDERED"],
    "__WORKSPACE_PATH__": os.environ["WORKSPACE_PATH"],
    "__LEADER_MODEL_ID__": os.environ["LEADER_MODEL_ID"],
    "__EXECUTOR_MODEL_ID__": os.environ["EXECUTOR_MODEL_ID"],
    "__REVIEWER_MODEL_ID__": os.environ["REVIEWER_MODEL_ID"],
    "__OPENCLAW_TIMEOUT_SECONDS__": os.environ["OPENCLAW_TIMEOUT_SECONDS"],
}

template = template_path.read_text(encoding="utf-8")
for key, value in placeholders.items():
    template = template.replace(key, value)

try:
    rendered = json.loads(template)
except json.JSONDecodeError as exc:
    print(f"Rendered OpenClaw config is invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

if config_path.exists():
    try:
        existing = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        existing = {}
        print(
            "Existing OpenClaw config is not valid JSON; rendering without preserving local runtime fields.",
            file=sys.stderr,
        )

    gateway_token = (
        existing.get("gateway", {})
        .get("auth", {})
        .get("token")
    )
    if gateway_token:
        rendered.setdefault("gateway", {}).setdefault("auth", {})["token"] = gateway_token

    ollama_api_key = (
        existing.get("models", {})
        .get("providers", {})
        .get("ollama", {})
        .get("apiKey")
    )
    if ollama_api_key:
        rendered.setdefault("models", {}).setdefault("providers", {}).setdefault("ollama", {})["apiKey"] = ollama_api_key

tmp_path.write_text(json.dumps(rendered, indent=2) + "\n", encoding="utf-8")
PY

python3 - <<'PY'
import json
import os
import pathlib

tmp_path = pathlib.Path(os.environ["TMP_PATH"])
json.loads(tmp_path.read_text(encoding="utf-8"))
PY

if [[ -f "$CONFIG_PATH" ]]; then
  BACKUP_PATH="$(mktemp "${CONFIG_PATH}.bak.$(date '+%Y%m%d_%H%M%S').XXXXXX")"
  cp "$CONFIG_PATH" "$BACKUP_PATH"
  log "Backup creado en $BACKUP_PATH"
fi

mv "$TMP_PATH" "$CONFIG_PATH"

log "Config renderizada en $CONFIG_PATH"
log "Workspace: $WORKSPACE_PATH"
log "Ollama base URL: $OLLAMA_BASE_URL_RENDERED"
log "Leader model: $LEADER_MODEL_ID"
log "Executor model: $EXECUTOR_MODEL_ID"
log "Reviewer model: $REVIEWER_MODEL_ID"
log "Agent timeout seconds: $OPENCLAW_TIMEOUT_SECONDS"

if [[ -x "$HOME/.openclaw/bin/openclaw" ]]; then
  if [[ "$CONFIG_PATH" == "$HOME/.openclaw/openclaw.json" ]]; then
    if "$HOME/.openclaw/bin/openclaw" config validate >/dev/null 2>&1; then
      log "OpenClaw config validate: OK"
    else
      warn "OpenClaw pudo leer la config JSON, pero 'openclaw config validate' reportó un problema."
    fi
  else
    warn "Se omitió 'openclaw config validate' porque la CLI solo valida la ruta por defecto (~/.openclaw/openclaw.json)."
  fi
fi
