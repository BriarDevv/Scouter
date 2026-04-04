#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[dev-up] %s\n' "$*"
}

warn() {
  printf '[dev-up] WARN: %s\n' "$*" >&2
}

die() {
  printf '[dev-up] ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$REPO_ROOT/.dev-runtime"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
DASHBOARD_LOG="$RUNTIME_DIR/dashboard.log"
BACKEND_PIDFILE="$RUNTIME_DIR/backend.pid"
DASHBOARD_PIDFILE="$RUNTIME_DIR/dashboard.pid"

BACKEND_PORT=8000
DASHBOARD_PORT=3000
LEGACY_BACKEND_PORT=8010
LEGACY_DASHBOARD_PORT=3001
PORTS_TO_CLEAR=("$DASHBOARD_PORT" "$LEGACY_DASHBOARD_PORT" "$BACKEND_PORT" "$LEGACY_BACKEND_PORT")

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "No encontré el comando requerido: $1"
}

listener_pids_for_port() {
  local port="$1"
  ss -ltnpH "( sport = :$port )" 2>/dev/null \
    | grep -o 'pid=[0-9]\+' \
    | cut -d= -f2 \
    | sort -u
}

process_matches_port_owner() {
  local port="$1"
  local pid="$2"
  local cmd
  cmd="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  case "$port" in
    3000|3001) [[ "$cmd" == *"next dev"* || "$cmd" == *"next-server"* ]] ;;&
    8000|8010) [[ "$cmd" == *"uvicorn app.main:app"* ]] ;;&
    *) return 1 ;;&
  esac
}


record_listener_pid() {
  local port="$1"
  local pidfile="$2"
  local label="$3"
  local pid

  pid="$(listener_pids_for_port "$port" | head -n 1 || true)"
  [[ -n "$pid" ]] || die "No pude detectar el PID de $label en el puerto $port"
  printf '%s\n' "$pid" >"$pidfile"
}

kill_listeners_for_port() {
  local port="$1"
  local -a pids=()
  mapfile -t pids < <(listener_pids_for_port "$port" || true)
  [[ ${#pids[@]} -gt 0 ]] || return 0

  local -a owned=()
  for pid in "${pids[@]}"; do
    if process_matches_port_owner "$port" "$pid"; then
      owned+=("$pid")
    fi
  done
  if [[ ${#owned[@]} -eq 0 ]]; then
    die "El puerto $port está ocupado por un proceso ajeno a Scouter; no lo voy a matar automáticamente"
  fi

  log "Liberando puerto $port (PIDs: ${owned[*]})"
  kill "${owned[@]}" 2>/dev/null || true
  sleep 1

  mapfile -t pids < <(listener_pids_for_port "$port" || true)
  if [[ ${#pids[@]} -gt 0 ]]; then
    warn "El puerto $port sigue ocupado; forzando kill -9 (${owned[*]})"
    kill -9 "${owned[@]}" 2>/dev/null || true
    sleep 1
  fi

  mapfile -t pids < <(listener_pids_for_port "$port" || true)
  [[ ${#pids[@]} -eq 0 ]] || die "No pude liberar el puerto $port"
}

wait_for_url() {
  local url="$1"
  local label="$2"
  local timeout_seconds="$3"
  local attempt

  for ((attempt = 1; attempt <= timeout_seconds; attempt++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$label listo en $url"
      return 0
    fi
    sleep 1
  done

  die "Timeout esperando $label en $url"
}

ensure_prereqs() {
  require_cmd bash
  require_cmd curl
  require_cmd ss
  require_cmd npm

  [[ -x "$REPO_ROOT/.venv/bin/python" ]] || die "Falta python en $REPO_ROOT/.venv"
  [[ -f "$REPO_ROOT/alembic.ini" ]] || die "No encontré alembic.ini en $REPO_ROOT"

  if [[ ! -d "$REPO_ROOT/dashboard/node_modules" ]]; then
    log "node_modules no existe; ejecutando npm ci en dashboard"
    (cd "$REPO_ROOT/dashboard" && npm ci)
  fi
}

run_migrations() {
  log "Aplicando migraciones pendientes"
  (
    cd "$REPO_ROOT"
    .venv/bin/python -m alembic upgrade head
  )
}

start_backend() {
  log "Levantando backend real en 127.0.0.1:$BACKEND_PORT"
  setsid -f bash -lc "cd '$REPO_ROOT' && exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port '$BACKEND_PORT' >'$BACKEND_LOG' 2>&1"
}

start_dashboard() {
  log "Levantando dashboard real en 127.0.0.1:$DASHBOARD_PORT"
  setsid -f bash -lc "cd '$REPO_ROOT/dashboard' && exec npm run dev >'$DASHBOARD_LOG' 2>&1"
}

mkdir -p "$RUNTIME_DIR"

ensure_prereqs

for port in "${PORTS_TO_CLEAR[@]}"; do
  kill_listeners_for_port "$port"
done

run_migrations
start_backend
wait_for_url "http://127.0.0.1:$BACKEND_PORT/health" "Backend" 30
wait_for_url "http://127.0.0.1:$BACKEND_PORT/api/v1/settings/mail" "Settings mail API" 30
record_listener_pid "$BACKEND_PORT" "$BACKEND_PIDFILE" "backend"
start_dashboard
wait_for_url "http://127.0.0.1:$DASHBOARD_PORT/settings" "Dashboard" 60
record_listener_pid "$DASHBOARD_PORT" "$DASHBOARD_PIDFILE" "dashboard"

log "Stack local real levantado"
log "Backend log: $BACKEND_LOG"
log "Dashboard log: $DASHBOARD_LOG"
log "Backend URL: http://127.0.0.1:$BACKEND_PORT"
log "Dashboard URL: http://127.0.0.1:$DASHBOARD_PORT"
