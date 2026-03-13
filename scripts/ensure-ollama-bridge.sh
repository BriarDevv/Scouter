#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[ensure-ollama-bridge] %s\n' "$*"
}

warn() {
  printf '[ensure-ollama-bridge] WARN: %s\n' "$*" >&2
}

die() {
  printf '[ensure-ollama-bridge] ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PS_SCRIPT="$REPO_ROOT/scripts/ensure-ollama-bridge.ps1"

OPENCLAW_OLLAMA_PORT="${OPENCLAW_OLLAMA_PORT:-11435}"
WSL_DISTRO="${OPENCLAW_WSL_DISTRO:-${WSL_DISTRO_NAME:-Ubuntu}}"
QUIET=0
PRINT_URL_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet)
      QUIET=1
      shift
      ;;
    --print-url)
      PRINT_URL_ONLY=1
      shift
      ;;
    *)
      die "Argumento desconocido: $1"
      ;;
  esac
done

command -v powershell.exe >/dev/null 2>&1 || die "No encontré powershell.exe para crear el bridge de Ollama en Windows."
[[ -f "$PS_SCRIPT" ]] || die "No encontré el helper PowerShell: $PS_SCRIPT"

PS_PATH="$(wslpath -w "$PS_SCRIPT")"

RAW_RESULT="$(
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$PS_PATH" -Distro "$WSL_DISTRO" -Port "$OPENCLAW_OLLAMA_PORT" -Json |
    tr -d '\r'
)"

[[ -n "$RAW_RESULT" ]] || die "El helper de bridge no devolvió salida."

BASE_URL="$(python3 - "$RAW_RESULT" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if not payload.get("ok"):
    raise SystemExit(1)
print(payload["base_url"])
PY
)" || {
  ERR_MSG="$(python3 - "$RAW_RESULT" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("error", "Error desconocido al crear el bridge de Ollama."))
PY
)"
  die "$ERR_MSG"
}

if (( PRINT_URL_ONLY == 1 )); then
  printf '%s\n' "$BASE_URL"
  exit 0
fi

if (( QUIET == 0 )); then
  STARTED="$(python3 - "$RAW_RESULT" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
print("true" if payload.get("started") else "false")
PY
)"
  PID="$(python3 - "$RAW_RESULT" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("pid", ""))
PY
)"
  PROBE="$(python3 - "$RAW_RESULT" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
print(payload.get("probe", ""))
PY
)"
  log "Bridge listo: $BASE_URL"
  log "Instancia nueva: $STARTED"
  [[ -n "$PID" ]] && log "PID Windows: $PID"
  [[ -n "$PROBE" ]] && log "Probe: $PROBE"
fi
