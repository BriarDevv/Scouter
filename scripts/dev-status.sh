#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[dev-status] %s\n' "$*"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.dev-runtime"
BACKEND_PIDFILE="$RUNTIME_DIR/backend.pid"
DASHBOARD_PIDFILE="$RUNTIME_DIR/dashboard.pid"

check_url() {
  local url="$1"
  local label="$2"
  python3 - "$url" "$label" <<'PY'
import sys
import urllib.error
import urllib.request

url = sys.argv[1]
label = sys.argv[2]

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(f"{label}: OK ({response.status})")
except Exception as exc:  # noqa: BLE001
    print(f"{label}: FAIL ({exc})")
PY
}

show_pidfile_status() {
  local pidfile="$1"
  local label="$2"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      log "$label pidfile: PID $pid activo"
      return
    fi
    log "$label pidfile: stale"
    return
  fi
  log "$label pidfile: missing"
}

log "Puertos activos (3000/3001/8000/8010)"
ss -ltnp | grep -E ':(3000|3001|8000|8010)\b' || log "No hay listeners en esos puertos"

show_pidfile_status "$BACKEND_PIDFILE" "backend"
show_pidfile_status "$DASHBOARD_PIDFILE" "dashboard"

check_url "http://127.0.0.1:8000/health" "backend /health"
check_url "http://127.0.0.1:8000/api/v1/settings/mail" "backend /api/v1/settings/mail"
check_url "http://127.0.0.1:8000/api/v1/mail/inbound/status" "backend /api/v1/mail/inbound/status"
check_url "http://127.0.0.1:3000/settings" "dashboard /settings"
check_url "http://127.0.0.1:3000/responses" "dashboard /responses"
