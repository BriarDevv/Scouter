#!/usr/bin/env bash
# ============================================================================
# Scouter — Script de gestion unificado
# Uso: ./scripts/scouter.sh {start|stop|restart|status|logs|preflight|seed|nuke}
#      o via Make: make up | make down | make status | make logs
# ============================================================================

set -euo pipefail

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
RUNTIME_DIR="$PROJECT_DIR/.dev-runtime"
PID_DIR="$PROJECT_DIR/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# ─── Helpers ───────────────────────────────────────────────────────────────

log_ok()   { echo -e "  ${GREEN}✔${NC} $1"; }
log_fail() { echo -e "  ${RED}✘${NC} $1"; }
log_info() { echo -e "  ${CYAN}→${NC} $1"; }
log_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

legacy_container_present() {
    local legacy_project
    legacy_project="$(printf '%s%s' 'claw' 'scout')"
    docker ps -a --format '{{.Names}}' | grep -Eq "^${legacy_project}-(postgres|redis)-1$"
}

is_running() {
    local pidfile="$PID_DIR/$1.pid"
    if [[ -f "$pidfile" ]]; then
        local pid
        pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        rm -f "$pidfile"
    fi
    return 1
}

get_pid() {
    local pidfile="$PID_DIR/$1.pid"
    [[ -f "$pidfile" ]] && cat "$pidfile"
}

record_background_pid() {
    local pattern="$1"
    local pidfile="$2"
    local label="$3"
    local pid

    pid="$(pgrep -f "$pattern" | head -n 1 || true)"
    [[ -n "$pid" ]] || {
        log_warn "$label no arrancó — ver logs"
        return 1
    }
    printf '%s\n' "$pid" >"$pidfile"
    return 0
}

# ─── Start ─────────────────────────────────────────────────────────────────

cmd_start() {
    echo -e "\n${BOLD}🚀 Encendiendo Scouter${NC}\n"

    if legacy_container_present; then
        log_info "Detectado stack Docker legado; migrando volumenes y limpiando contenedores viejos..."
    fi
    bash "$SCRIPT_DIR/migrate-legacy-stack.sh"

    # 1. Docker infra (postgres + redis)
    if docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q postgres; then
        log_ok "Postgres ya esta corriendo"
    else
        log_info "Levantando Postgres + Redis..."
        docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d postgres redis >/dev/null 2>&1
        sleep 3
        if docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q postgres; then
            log_ok "Postgres + Redis levantados"
        else
            log_fail "No se pudo levantar Postgres/Redis"
            return 1
        fi
    fi

    # 2. API + Dashboard via dev-up.sh (maneja migraciones, puertos, PIDs)
    log_info "Levantando API + Dashboard (via dev-up.sh)..."
    echo ""
    bash "$SCRIPT_DIR/dev-up.sh"

    # 3. Celery worker
    if is_running worker; then
        log_ok "Worker ya esta corriendo (PID $(get_pid worker))"
    else
        if [[ ! -x "$PROJECT_DIR/.venv/bin/python" ]]; then
            log_fail "No se encontro .venv — ejecutar: python3 -m venv .venv && python -m pip install -e '.[dev]'"
            return 1
        fi
        log_info "Iniciando Celery worker..."
        setsid -f bash -lc "cd '$PROJECT_DIR' && exec '$PROJECT_DIR/.venv/bin/python' -m celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 -Q default,enrichment,scoring,llm,reviewer,research >>'$LOG_DIR/worker.log' 2>&1"
        sleep 2
        if record_background_pid ".venv/bin/python -m celery -A app.workers.celery_app worker" "$PID_DIR/worker.pid" "Worker" && is_running worker; then
            log_ok "Worker corriendo (PID $(get_pid worker))"
        else
            log_warn "Worker no arranco — ver logs/worker.log"
        fi
    fi

    # 3b. Celery beat (scheduler for janitor and periodic tasks)
    if is_running beat; then
        log_ok "Beat ya esta corriendo (PID $(get_pid beat))"
    else
        log_info "Iniciando Celery beat..."
        setsid -f bash -lc "cd '$PROJECT_DIR' && exec '$PROJECT_DIR/.venv/bin/python' -m celery -A app.workers.celery_app beat --loglevel=info >>'$LOG_DIR/beat.log' 2>&1"
        sleep 2
        if record_background_pid ".venv/bin/python -m celery -A app.workers.celery_app beat" "$PID_DIR/beat.pid" "Beat" && is_running beat; then
            log_ok "Beat corriendo (PID $(get_pid beat))"
        else
            log_warn "Beat no arranco — ver logs/beat.log"
        fi
    fi

    echo ""
    echo -e "${BOLD}Todo encendido.${NC} Servicios:"
    echo -e "  Dashboard:   ${CYAN}http://localhost:3000${NC}"
    echo -e "  API/Swagger:  ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Health:       ${CYAN}http://localhost:8000/health/detailed${NC}"
    echo ""
}

# ─── Stop ──────────────────────────────────────────────────────────────────

cmd_stop() {
    echo -e "\n${BOLD}🛑 Apagando Scouter${NC}\n"

    # 1. API + Dashboard via dev-down.sh
    log_info "Deteniendo API + Dashboard (via dev-down.sh)..."
    bash "$SCRIPT_DIR/dev-down.sh"

    # 2. Celery worker
    if is_running worker; then
        local pid
        pid=$(get_pid worker)
        kill "$pid" 2>/dev/null || true
        rm -f "$PID_DIR/worker.pid"
        log_ok "Worker detenido (was PID $pid)"
    else
        log_info "Worker no estaba corriendo"
    fi

    # 2b. Celery beat
    if is_running beat; then
        local pid
        pid=$(get_pid beat)
        kill "$pid" 2>/dev/null || true
        rm -f "$PID_DIR/beat.pid"
        log_ok "Beat detenido (was PID $pid)"
    else
        log_info "Beat no estaba corriendo"
    fi

    # 3. Docker infra
    log_info "Deteniendo Postgres + Redis..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" stop postgres redis >/dev/null 2>&1 || true
    log_ok "Infraestructura detenida"

    echo ""
    echo -e "${DIM}Datos de Postgres/Redis conservados. Usar '$0 nuke' para borrarlos.${NC}"
    echo ""
}

# ─── Status ────────────────────────────────────────────────────────────────

cmd_status() {
    echo -e "\n${BOLD}📊 Estado de Scouter${NC}\n"

    if legacy_container_present; then
        log_warn "Hay contenedores Docker legados del nombre anterior; ejecutar './scripts/scouter.sh start' para migrarlos"
    fi

    # Docker services
    for svc in postgres redis; do
        if docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q "$svc"; then
            log_ok "$svc corriendo (Docker)"
        else
            log_fail "$svc no esta corriendo"
        fi
    done

    # Celery worker
    if is_running worker; then
        log_ok "worker corriendo (PID $(get_pid worker))"
    else
        log_fail "worker no esta corriendo"
    fi

    # Celery beat
    if is_running beat; then
        log_ok "beat corriendo (PID $(get_pid beat))"
    else
        log_fail "beat no esta corriendo"
    fi

    # API + Dashboard via dev-status.sh
    echo ""
    bash "$SCRIPT_DIR/dev-status.sh"

    echo ""
}

# ─── Logs ──────────────────────────────────────────────────────────────────

cmd_logs() {
    local service="${1:-all}"

    case "$service" in
        api|backend)
            local logfile="$RUNTIME_DIR/backend.log"
            [[ -f "$logfile" ]] || logfile="$LOG_DIR/api.log"
            if [[ -f "$logfile" ]]; then
                echo -e "${DIM}Logs de API (Ctrl+C para salir)${NC}\n"
                tail -f "$logfile"
            else
                log_fail "No hay logs de API todavia"
            fi
            ;;
        dashboard)
            local logfile="$RUNTIME_DIR/dashboard.log"
            [[ -f "$logfile" ]] || logfile="$LOG_DIR/dashboard.log"
            if [[ -f "$logfile" ]]; then
                echo -e "${DIM}Logs de Dashboard (Ctrl+C para salir)${NC}\n"
                tail -f "$logfile"
            else
                log_fail "No hay logs de Dashboard todavia"
            fi
            ;;
        worker)
            if [[ -f "$LOG_DIR/worker.log" ]]; then
                echo -e "${DIM}Logs de Worker (Ctrl+C para salir)${NC}\n"
                tail -f "$LOG_DIR/worker.log"
            else
                log_fail "No hay logs de Worker todavia"
            fi
            ;;
        all)
            echo -e "${DIM}Mostrando todos los logs (Ctrl+C para salir)${NC}\n"
            tail -f "$RUNTIME_DIR"/*.log "$LOG_DIR"/*.log 2>/dev/null || echo "No hay logs todavia"
            ;;
        *)
            echo "Servicios: api, worker, dashboard, all"
            ;;
    esac
}

# ─── Preflight ─────────────────────────────────────────────────────────────

cmd_preflight() {
    cd "$PROJECT_DIR"
    if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source "$PROJECT_DIR/.venv/bin/activate"
    fi
    python3 scripts/preflight.py
}

# ─── Seed ──────────────────────────────────────────────────────────────────

cmd_seed() {
    cd "$PROJECT_DIR"
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"
    python3 scripts/seed.py
}

# ─── Nuke ──────────────────────────────────────────────────────────────────

cmd_nuke() {
    echo -e "\n${RED}${BOLD}⚠ NUKE: Esto va a parar todo y BORRAR los datos de Postgres y Redis${NC}\n"
    read -r -p "Estas seguro? (escribi 'si' para confirmar): " confirm
    if [[ "$confirm" != "si" ]]; then
        echo "Cancelado."
        return
    fi

    cmd_stop
    log_info "Borrando volumenes de Docker..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" down -v >/dev/null 2>&1 || true
    log_ok "Volumenes borrados"

    log_info "Limpiando logs y PIDs..."
    rm -rf "$LOG_DIR"/* "$PID_DIR"/* "$RUNTIME_DIR"/*
    log_ok "Limpio"

    echo ""
}

# ─── Restart ───────────────────────────────────────────────────────────────

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

# ─── Main ──────────────────────────────────────────────────────────────────

usage() {
    echo -e "${BOLD}Scouter${NC} — Script de gestion\n"
    echo "Uso: $0 {comando}"
    echo ""
    echo "Comandos:"
    echo "  start       Encender todo (Postgres, Redis, API, Worker, Dashboard)"
    echo "  stop        Apagar todo (mantiene datos)"
    echo "  restart     Apagar + encender"
    echo "  status      Ver que esta corriendo"
    echo "  logs [svc]  Ver logs en vivo (api|worker|dashboard|all)"
    echo "  preflight   Verificar que todo esta configurado"
    echo "  seed        Cargar datos de prueba"
    echo "  nuke        Parar todo Y borrar datos (pide confirmacion)"
    echo ""
    echo "Atajos via Make:"
    echo "  make up       = ./scripts/scouter.sh start"
    echo "  make down     = ./scripts/scouter.sh stop"
    echo "  make status   = ./scripts/scouter.sh status"
    echo "  make logs     = ./scripts/scouter.sh logs"
    echo "  make restart  = ./scripts/scouter.sh restart"
    echo ""
}

case "${1:-}" in
    start)     cmd_start ;;
    stop)      cmd_stop ;;
    restart)   cmd_restart ;;
    status)    cmd_status ;;
    logs)      cmd_logs "${2:-all}" ;;
    preflight) cmd_preflight ;;
    seed)      cmd_seed ;;
    nuke)      cmd_nuke ;;
    *)         usage ;;
esac
