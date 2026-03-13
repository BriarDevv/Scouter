#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[dev-down] %s\n' "$*"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.dev-runtime"
BACKEND_PIDFILE="$RUNTIME_DIR/backend.pid"
DASHBOARD_PIDFILE="$RUNTIME_DIR/dashboard.pid"

PORTS_TO_CLEAR=(3000 3001 8000 8010)

listener_pids_for_port() {
  local port="$1"
  ss -ltnpH "( sport = :$port )" 2>/dev/null \
    | grep -o 'pid=[0-9]\+' \
    | cut -d= -f2 \
    | sort -u
}

kill_pidfile_process() {
  local pidfile="$1"
  local label="$2"
  if [[ -f "$pidfile" ]]; then
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      log "Deteniendo $label (PID $pid)"
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  fi
}

kill_listeners_for_port() {
  local port="$1"
  local -a pids=()
  mapfile -t pids < <(listener_pids_for_port "$port" || true)
  [[ ${#pids[@]} -gt 0 ]] || return 0
  log "Liberando puerto $port (PIDs: ${pids[*]})"
  kill "${pids[@]}" 2>/dev/null || true
  sleep 1
  mapfile -t pids < <(listener_pids_for_port "$port" || true)
  if [[ ${#pids[@]} -gt 0 ]]; then
    kill -9 "${pids[@]}" 2>/dev/null || true
  fi
}

kill_pidfile_process "$BACKEND_PIDFILE" "backend"
kill_pidfile_process "$DASHBOARD_PIDFILE" "dashboard"

for port in "${PORTS_TO_CLEAR[@]}"; do
  kill_listeners_for_port "$port"
done

log "Runtime local detenido"
