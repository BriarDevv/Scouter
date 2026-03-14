#!/usr/bin/env bash
# ============================================================================
# ClawScout — Script de gestion
# Uso: ./scripts/clawscout.sh {start|stop|restart|status|logs|preflight|seed|nuke}
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

# Detectar directorio del proyecto (donde esta este script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/.pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

# ─── Helpers ───────────────────────────────────────────────────────────────

log_ok()   { echo -e "  ${GREEN}✔${NC} $1"; }
log_fail() { echo -e "  ${RED}✘${NC} $1"; }
log_info() { echo -e "  ${CYAN}→${NC} $1"; }
log_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

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

wait_for_port() {
    local port=$1
    local name=$2
    local timeout=${3:-30}
    local elapsed=0
    while ! ss -tlnp 2>/dev/null | grep -q ":${port} " && [[ $elapsed -lt $timeout ]]; do
        sleep 1
        ((elapsed++))
    done
    if [[ $elapsed -ge $timeout ]]; then
        log_warn "$name no respondio en ${timeout}s (puerto $port)"
        return 1
    fi
    return 0
}

# ─── Start ─────────────────────────────────────────────────────────────────

cmd_start() {
    echo -e "\n${BOLD}🚀 Encendiendo ClawScout${NC}\n"

    # 1. Docker infra (postgres + redis)
    if docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q postgres; then
        log_ok "Postgres ya esta corriendo"
    else
        log_info "Levantando Postgres + Redis..."
        docker compose -f "$PROJECT_DIR/docker-compose.yml" up -d postgres redis >/dev/null 2>&1
        sleep 2
        if docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q postgres; then
            log_ok "Postgres + Redis levantados"
        else
            log_fail "No se pudo levantar Postgres/Redis"
            return 1
        fi
    fi

    # 2. Activar venv
    if [[ ! -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
        log_fail "No se encontro .venv — ejecutar: python3 -m venv .venv && pip install -e '.[dev]'"
        return 1
    fi
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"

    # 3. Migraciones
    log_info "Verificando migraciones..."
    cd "$PROJECT_DIR"
    if alembic check 2>/dev/null; then
        log_ok "Migraciones al dia"
    else
        log_info "Aplicando migraciones..."
        alembic upgrade head 2>>"$LOG_DIR/alembic.log"
        log_ok "Migraciones aplicadas"
    fi

    # 4. API (uvicorn)
    if is_running api; then
        log_ok "API ya esta corriendo (PID $(get_pid api))"
    else
        log_info "Iniciando API en :8000..."
        cd "$PROJECT_DIR"
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 \
            >>"$LOG_DIR/api.log" 2>&1 &
        echo $! > "$PID_DIR/api.pid"
        if wait_for_port 8000 "API" 15; then
            log_ok "API corriendo en :8000 (PID $(get_pid api))"
        fi
    fi

    # 5. Celery worker
    if is_running worker; then
        log_ok "Worker ya esta corriendo (PID $(get_pid worker))"
    else
        log_info "Iniciando Celery worker..."
        cd "$PROJECT_DIR"
        nohup celery -A app.workers.celery_app worker \
            --loglevel=info --concurrency=2 \
            >>"$LOG_DIR/worker.log" 2>&1 &
        echo $! > "$PID_DIR/worker.pid"
        sleep 2
        if is_running worker; then
            log_ok "Worker corriendo (PID $(get_pid worker))"
        else
            log_warn "Worker no arranco — ver logs/worker.log"
        fi
    fi

    # 6. Dashboard (Next.js)
    if is_running dashboard; then
        log_ok "Dashboard ya esta corriendo (PID $(get_pid dashboard))"
    else
        if [[ ! -d "$PROJECT_DIR/dashboard/node_modules" ]]; then
            log_warn "node_modules no encontrado — ejecutar: cd dashboard && npm ci"
        else
            log_info "Iniciando Dashboard en :3000..."
            cd "$PROJECT_DIR/dashboard"
            nohup npm run dev \
                >>"$LOG_DIR/dashboard.log" 2>&1 &
            echo $! > "$PID_DIR/dashboard.pid"
            if wait_for_port 3000 "Dashboard" 20; then
                log_ok "Dashboard corriendo en :3000 (PID $(get_pid dashboard))"
            fi
        fi
    fi

    echo ""
    echo -e "${BOLD}Servicios:${NC}"
    echo -e "  Dashboard:  ${CYAN}http://localhost:3000${NC}"
    echo -e "  API/Swagger: ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  Health:      ${CYAN}http://localhost:8000/health/detailed${NC}"
    echo ""
}

# ─── Stop ──────────────────────────────────────────────────────────────────

cmd_stop() {
    echo -e "\n${BOLD}🛑 Apagando ClawScout${NC}\n"

    for svc in dashboard worker api; do
        if is_running "$svc"; then
            local pid
            pid=$(get_pid "$svc")
            # Kill the process tree (para npm/node children)
            kill -- -"$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')" 2>/dev/null || kill "$pid" 2>/dev/null || true
            rm -f "$PID_DIR/$svc.pid"
            log_ok "$svc detenido (was PID $pid)"
        else
            log_info "$svc no estaba corriendo"
        fi
    done

    # Docker infra
    log_info "Deteniendo Postgres + Redis..."
    docker compose -f "$PROJECT_DIR/docker-compose.yml" stop postgres redis >/dev/null 2>&1 || true
    log_ok "Infraestructura detenida"

    echo ""
    echo -e "${DIM}Datos de Postgres/Redis conservados. Usar './scripts/clawscout.sh nuke' para borrarlos.${NC}"
    echo ""
}

# ─── Status ────────────────────────────────────────────────────────────────

cmd_status() {
    echo -e "\n${BOLD}📊 Estado de ClawScout${NC}\n"

    # Docker services
    for svc in postgres redis; do
        if docker compose -f "$PROJECT_DIR/docker-compose.yml" ps --status running 2>/dev/null | grep -q "$svc"; then
            log_ok "$svc corriendo (Docker)"
        else
            log_fail "$svc no esta corriendo"
        fi
    done

    # App services
    for svc in api worker dashboard; do
        if is_running "$svc"; then
            local pid
            pid=$(get_pid "$svc")
            local port=""
            case $svc in
                api) port=":8000" ;;
                dashboard) port=":3000" ;;
            esac
            log_ok "$svc corriendo (PID $pid)${port:+ en $port}"
        else
            log_fail "$svc no esta corriendo"
        fi
    done

    # Health check
    echo ""
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        log_ok "API respondiendo en /health"
        # Try detailed health
        local health
        health=$(curl -sf http://localhost:8000/health/detailed 2>/dev/null || echo "")
        if [[ -n "$health" ]]; then
            echo -e "\n  ${DIM}Health detallado:${NC}"
            echo "$health" | python3 -m json.tool 2>/dev/null | sed 's/^/    /'
        fi
    else
        log_warn "API no responde"
    fi

    echo ""
}

# ─── Logs ──────────────────────────────────────────────────────────────────

cmd_logs() {
    local service="${1:-all}"

    if [[ "$service" == "all" ]]; then
        echo -e "${DIM}Mostrando todos los logs (Ctrl+C para salir)${NC}\n"
        tail -f "$LOG_DIR"/*.log 2>/dev/null || echo "No hay logs todavia"
    else
        local logfile="$LOG_DIR/$service.log"
        if [[ -f "$logfile" ]]; then
            echo -e "${DIM}Logs de $service (Ctrl+C para salir)${NC}\n"
            tail -f "$logfile"
        else
            log_fail "No se encontro $logfile"
            echo -e "  Servicios disponibles: api, worker, dashboard, alembic"
        fi
    fi
}

# ─── Preflight ─────────────────────────────────────────────────────────────

cmd_preflight() {
    cd "$PROJECT_DIR"
    if [[ -f "$PROJECT_DIR/.venv/bin/activate" ]]; then
        source "$PROJECT_DIR/.venv/bin/activate"
    fi
    python3 scripts/preflight.py
}

# ─── Seed ──────────────────────────────────────────────────────────────────

cmd_seed() {
    cd "$PROJECT_DIR"
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
    rm -rf "$LOG_DIR"/* "$PID_DIR"/*
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
    echo -e "${BOLD}ClawScout${NC} — Script de gestion\n"
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
