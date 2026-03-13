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
  default            Run checks, render OpenClaw config, and print exact local start commands.
  --launch           Additionally start selected services in tmux when safe.

Services:
  backend
  worker
  dashboard
  openclaw

Examples:
  scripts/start-local-stack.sh
  scripts/start-local-stack.sh --launch
  scripts/start-local-stack.sh --launch --service backend --service worker

Environment overrides:
  OPENCLAW_OLLAMA_BASE_URL
  OPENCLAW_OLLAMA_HOST
  OPENCLAW_OLLAMA_PORT
  OPENCLAW_WORKSPACE
  OPENCLAW_LEADER_MODEL
  OPENCLAW_EXECUTOR_MODEL
  OPENCLAW_REVIEWER_MODEL
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RENDER_SCRIPT="$REPO_ROOT/scripts/render-openclaw-config.sh"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw/openclaw.json}"
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
    --backend|--worker|--dashboard|--openclaw)
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
    REQUESTED_SERVICES=(backend worker dashboard openclaw)
  fi

  for item in "${REQUESTED_SERVICES[@]}"; do
    case "$item" in
      backend|worker|dashboard|openclaw)
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
      printf "cd %q && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000" "$REPO_ROOT"
      ;;
    worker)
      printf "cd %q && .venv/bin/celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --pool=prefork --queues=default,enrichment,scoring,llm,reviewer --hostname=clawscout-wsl" "$REPO_ROOT"
      ;;
    dashboard)
      printf "cd %q && npm run dev -- --hostname 0.0.0.0 --port 3000" "$REPO_ROOT/dashboard"
      ;;
    openclaw)
      printf "%q gateway run --port 18789 --verbose" "$HOME/.openclaw/bin/openclaw"
      ;;
    *)
      die "Servicio no soportado: $1"
      ;;
  esac
}

service_session() {
  case "$1" in
    backend) printf 'clawscout-api' ;;
    worker) printf 'clawscout-worker' ;;
    dashboard) printf 'clawscout-dashboard' ;;
    openclaw) printf 'openclaw-gw' ;;
    *) die "Servicio no soportado: $1" ;;
  esac
}

service_pattern() {
  case "$1" in
    backend) printf 'uvicorn app.main:app --host 0.0.0.0 --port 8000' ;;
    worker) printf 'celery -A app.workers.celery_app worker' ;;
    dashboard) printf 'next dev --hostname 0.0.0.0 --port 3000' ;;
    openclaw) printf 'openclaw gateway run --port 18789' ;;
    *) die "Servicio no soportado: $1" ;;
  esac
}

service_url() {
  case "$1" in
    backend) printf 'http://127.0.0.1:8000/docs' ;;
    worker) printf 'n/a (Celery worker)' ;;
    dashboard) printf 'http://127.0.0.1:3000' ;;
    openclaw) printf 'http://127.0.0.1:18789/' ;;
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
  local clawscout_ollama_base=""

  if docker info >/dev/null 2>&1; then
    docker_status="accesible desde WSL"
  elif command -v docker >/dev/null 2>&1; then
    docker_status="CLI presente, pero Docker Desktop no responde"
  fi

  if [[ -f "$ENV_FILE" ]]; then
    clawscout_ollama_base="$(parse_env_value "OLLAMA_BASE_URL" "$ENV_FILE" || true)"
  fi

  log "WSL detectado: OK"
  log "Repo root: $REPO_ROOT"
  log "Python: $(command -v python3)"
  log "Node: $(command -v node)"
  log "npm: $(command -v npm)"
  log "Docker: $docker_status"
  if [[ -n "$clawscout_ollama_base" ]]; then
    log "ClawScout .env OLLAMA_BASE_URL: $clawscout_ollama_base"
  else
    warn "No encontré OLLAMA_BASE_URL en $ENV_FILE"
  fi
}

render_openclaw_config() {
  [[ -x "$RENDER_SCRIPT" ]] || die "No encontré el renderer de OpenClaw: $RENDER_SCRIPT"
  "$RENDER_SCRIPT"
}

show_openclaw_config_summary() {
  python3 - "$OPENCLAW_CONFIG_PATH" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
provider = data["models"]["providers"]["ollama"]
defaults = data["agents"]["defaults"]
aliases = {}
for model_id, meta in defaults.get("models", {}).items():
    alias = meta.get("alias")
    if alias:
      aliases[alias] = model_id.split("/", 1)[1] if "/" in model_id else model_id
print(f"OPENCLAW_CONFIG_PATH={path}")
print(f"OPENCLAW_WORKSPACE={defaults['workspace']}")
print(f"OPENCLAW_OLLAMA_BASE_URL={provider['baseUrl']}")
print(f"OPENCLAW_LEADER_MODEL={aliases.get('leader', '')}")
print(f"OPENCLAW_EXECUTOR_MODEL={aliases.get('executor', '')}")
print(f"OPENCLAW_REVIEWER_MODEL={aliases.get('reviewer', '')}")
PY
}

print_start_guide() {
  local service
  printf '\n'
  log "Servicios locales"
  for service in backend worker dashboard openclaw; do
    printf '  - %-10s %s\n' "$service" "$(service_url "$service")"
  done

  printf '\n'
  log "Comandos exactos"
  printf '  - Infra      docker compose up -d postgres redis\n'
  printf '  - Backend    %s\n' "$(service_command backend)"
  printf '  - Worker     %s\n' "$(service_command worker)"
  printf '  - Dashboard  %s\n' "$(service_command dashboard)"
  printf '  - OpenClaw   %s\n' "$(service_command openclaw)"

  printf '\n'
  log "Smoke checks"
  printf '  - API health      curl http://127.0.0.1:8000/health\n'
  printf '  - Dashboard       curl -I http://127.0.0.1:3000\n'
  printf '  - OpenClaw        %q health\n' "$HOME/.openclaw/bin/openclaw"
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
  local key value rendered_base_url clawscout_base_url=""

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
  [[ -x "$REPO_ROOT/.venv/bin/uvicorn" ]] || warn "No encontré .venv/bin/uvicorn. Ejecutá 'pip install -e \".[dev]\"' en el venv Linux."
  [[ -x "$REPO_ROOT/.venv/bin/celery" ]] || warn "No encontré .venv/bin/celery. Ejecutá 'pip install -e \".[dev]\"' en el venv Linux."
  [[ -d "$REPO_ROOT/dashboard/node_modules" ]] || warn "No encontré dashboard/node_modules. Ejecutá 'cd dashboard && npm ci'."
  [[ -x "$HOME/.openclaw/bin/openclaw" ]] || warn "No encontré ~/.openclaw/bin/openclaw. OpenClaw no podrá arrancar."

  normalize_services
  show_prereq_status
  render_openclaw_config

  declare -A rendered
  while IFS='=' read -r key value; do
    rendered["$key"]="$value"
  done < <(show_openclaw_config_summary)

  rendered_base_url="${rendered[OPENCLAW_OLLAMA_BASE_URL]:-}"
  clawscout_base_url="$(parse_env_value "OLLAMA_BASE_URL" "$ENV_FILE" || true)"

  printf '\n'
  log "Config efectiva"
  printf '  - Workspace   %s\n' "${rendered[OPENCLAW_WORKSPACE]:-}"
  printf '  - Ollama      %s\n' "$rendered_base_url"
  printf '  - Leader      %s\n' "${rendered[OPENCLAW_LEADER_MODEL]:-}"
  printf '  - Executor    %s\n' "${rendered[OPENCLAW_EXECUTOR_MODEL]:-}"
  printf '  - Reviewer    %s\n' "${rendered[OPENCLAW_REVIEWER_MODEL]:-}"

  if [[ -n "$clawscout_base_url" && "$clawscout_base_url" != "$rendered_base_url" ]]; then
    warn "OLLAMA_BASE_URL de ClawScout ($clawscout_base_url) no coincide con OpenClaw ($rendered_base_url)."
  fi

  if [[ -n "$rendered_base_url" ]]; then
    if curl --silent --fail --max-time 5 "$rendered_base_url/api/tags" >/dev/null; then
      log "Ollama accesible desde WSL: OK"
    else
      warn "No pude alcanzar Ollama en $rendered_base_url/api/tags"
    fi
  fi

  if (( LAUNCH_MODE == 1 )); then
    for key in "${REQUESTED_SERVICES[@]}"; do
      start_service "$key"
    done
  fi

  print_start_guide
}

main "$@"
