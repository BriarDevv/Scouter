#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[start-local-stack] %s\n' "$*"
}

warn() {
  printf '[start-local-stack] WARN: %s\n' "$*" >&2
}

die() {
  printf '[start-local-stack] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage:
  scripts/start-local-stack.sh [--launch] [--service <name>]
  scripts/start-local-stack.sh --help

Modes:
  default            Run checks and print exact local start commands.
  --launch           Additionally start selected services in tmux when safe.

Services:
  backend
  worker
  dashboard

Examples:
  scripts/start-local-stack.sh
  scripts/start-local-stack.sh --launch
  scripts/start-local-stack.sh --launch --service backend --service worker
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
LAUNCH_MODE=0
declare -a REQUESTED_SERVICES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --launch)
      LAUNCH_MODE=1
      shift
      ;;
    --service)
      [[ $# -ge 2 ]] || die "Falta valor para --service"
      REQUESTED_SERVICES+=("$2")
      shift 2
      ;;
    --backend|--worker|--dashboard)
      REQUESTED_SERVICES+=("${1#--}")
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Argumento desconocido: $1"
      ;;
  esac
done

is_wsl() {
  [[ -n "${WSL_INTEROP:-}" ]] && return 0
  grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "No encontré el comando requerido: $1"
}

normalize_services() {
  local item
  local -a normalized=()
  if [[ ${#REQUESTED_SERVICES[@]} -eq 0 ]]; then
    REQUESTED_SERVICES=(backend worker dashboard)
  fi

  for item in "${REQUESTED_SERVICES[@]}"; do
    case "$item" in
      backend|worker|dashboard)
        if [[ ! " ${normalized[*]} " =~ " ${item} " ]]; then
          normalized+=("$item")
        fi
        ;;
      *)
        die "Servicio no soportado: $item"
        ;;
    esac
  done
  REQUESTED_SERVICES=("${normalized[@]}")
}

parse_env_value() {
  local key="$1"
  local path="$2"
  [[ -f "$path" ]] || return 1
  python3 - "$key" "$path" <<'PY'
import pathlib
import sys

key = sys.argv[1]
path = pathlib.Path(sys.argv[2])

for raw_line in path.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, value = line.split("=", 1)
    if name.strip() != key:
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    print(value)
    break
PY
}

service_command() {
  case "$1" in
    backend)
      printf "cd %q && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" "$REPO_ROOT"
      ;;
    worker)
      printf "cd %q && .venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --pool=prefork --queues=default,enrichment,scoring,llm,reviewer --hostname=scouter-wsl" "$REPO_ROOT"
      ;;
    dashboard)
      printf "cd %q && npm run dev -- --hostname 127.0.0.1 --port 3000" "$REPO_ROOT/dashboard"
      ;;
    *)
      die "Servicio no soportado: $1"
      ;;
  esac
}

service_session() {
  case "$1" in
    backend) printf 'scouter-api' ;;
    worker) printf 'scouter-worker' ;;
    dashboard) printf 'scouter-dashboard' ;;
    *) die "Servicio no soportado: $1" ;;
  esac
}

service_pattern() {
  case "$1" in
    backend) printf 'uvicorn app.main:app --host 127.0.0.1 --port 8000' ;;
    worker) printf 'celery -A app.workers.celery_app worker' ;;
    dashboard) printf 'next dev --hostname 127.0.0.1 --port 3000' ;;
    *) die "Servicio no soportado: $1" ;;
  esac
}

service_url() {
  case "$1" in
    backend) printf 'http://127.0.0.1:8000/docs' ;;
    worker) printf 'n/a (Celery worker)' ;;
    dashboard) printf 'http://127.0.0.1:3000' ;;
    *) die "Servicio no soportado: $1" ;;
  esac
}

session_exists() {
  tmux has-session -t "$1" >/dev/null 2>&1
}

process_exists() {
  pgrep -f "$1" >/dev/null 2>&1
}

start_service() {
  local service="$1"
  local session pattern command
  session="$(service_session "$service")"
  pattern="$(service_pattern "$service")"
  command="$(service_command "$service")"

  if session_exists "$session"; then
    log "Sesión tmux '$session' ya existe; no lanzo duplicado."
    return 0
  fi

  if process_exists "$pattern"; then
    warn "Detecté '$service' corriendo fuera de tmux; no lanzo duplicado."
    return 0
  fi

  tmux new-session -d -s "$session" "bash -lc '$command'"
  log "Servicio '$service' lanzado en tmux como '$session'."
}

show_prereq_status() {
  local docker_status="no disponible"
  local scouter_ollama_base=""

  if docker info >/dev/null 2>&1; then
    docker_status="accesible desde WSL"
  elif command -v docker >/dev/null 2>&1; then
    docker_status="CLI presente, pero Docker Desktop no responde"
  fi

  if [[ -f "$ENV_FILE" ]]; then
    scouter_ollama_base="$(parse_env_value "OLLAMA_BASE_URL" "$ENV_FILE" || true)"
  fi

  log "WSL detectado: OK"
  log "Repo root: $REPO_ROOT"
  log "Python: $(command -v python3)"
  log "Node: $(command -v node)"
  log "npm: $(command -v npm)"
  log "Docker: $docker_status"
  if [[ -n "$scouter_ollama_base" ]]; then
    log "Scouter .env OLLAMA_BASE_URL: $scouter_ollama_base"
  else
    warn "No encontré OLLAMA_BASE_URL en $ENV_FILE"
  fi
}

print_start_guide() {
  local service
  printf '\n'
  log "Servicios locales"
  for service in backend worker dashboard; do
    printf '  - %-10s %s\n' "$service" "$(service_url "$service")"
  done

  printf '\n'
  log "Comandos exactos"
  printf '  - Infra      docker compose up -d postgres redis\n'
  printf '  - Backend    %s\n' "$(service_command backend)"
  printf '  - Worker     %s\n' "$(service_command worker)"
  printf '  - Dashboard  %s\n' "$(service_command dashboard)"

  printf '\n'
  log "Smoke checks"
  printf '  - API health      curl http://127.0.0.1:8000/health\n'
  printf '  - Dashboard       curl -I http://127.0.0.1:3000\n'
  printf '  - Task status     curl http://127.0.0.1:8000/api/v1/tasks/<task_id>/status\n'

  if (( LAUNCH_MODE == 1 )); then
    printf '\n'
    log "Sesiones tmux útiles"
    for service in "${REQUESTED_SERVICES[@]}"; do
      printf '  - %-10s tmux attach -t %s\n' "$service" "$(service_session "$service")"
    done
  fi
}

main() {
  local key scouter_base_url=""

  is_wsl || die "Este script está pensado para WSL/Linux-first."

  require_cmd bash
  require_cmd python3
  require_cmd node
  require_cmd npm
  require_cmd ip
  if (( LAUNCH_MODE == 1 )); then
    require_cmd tmux
  elif ! command -v tmux >/dev/null 2>&1; then
    warn "No encontré tmux. El modo guía funciona igual, pero --launch no va a estar disponible."
  fi

  [[ -d "$REPO_ROOT/.venv" ]] || warn "No encontré $REPO_ROOT/.venv. Backend/worker no van a arrancar hasta crear el venv."
  [[ -x "$REPO_ROOT/.venv/bin/python" ]] || warn "No encontré .venv/bin/python. Ejecutá 'python -m pip install -e \".[dev]\"' en el venv Linux."
  [[ -x "$REPO_ROOT/.venv/bin/python" ]] || warn "No encontré .venv/bin/python. Ejecutá 'python -m pip install -e \".[dev]\"' en el venv Linux."
  [[ -d "$REPO_ROOT/dashboard/node_modules" ]] || warn "No encontré dashboard/node_modules. Ejecutá 'cd dashboard && npm ci'."

  normalize_services
  show_prereq_status

  if (( LAUNCH_MODE == 1 )); then
    for key in "${REQUESTED_SERVICES[@]}"; do
      start_service "$key"
    done
  fi

  print_start_guide
}

main "$@"
