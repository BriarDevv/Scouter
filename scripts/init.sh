#!/usr/bin/env bash
# ============================================================================
# Scouter Init — setup completo desde cero (ejecutar UNA sola vez)
# Prerequisitos: WSL2, Docker, Ollama, Python 3.12+, Node 20+
# Uso: bash scripts/init.sh
# ============================================================================
set -euo pipefail

echo "╔══════════════════════════════════════╗"
echo "║     Scouter Init                   ║"
echo "╚══════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# ── 0. Verificar prerequisitos ──────────────────────────────────────
echo "→ Verificando prerequisitos..."

# Python
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version 2>&1)
  echo "  ✔ $PY_VER"
else
  echo "  ✗ Python 3 no encontrado. Instalalo primero (ver README)."
  exit 1
fi

# Node
if command -v node &>/dev/null; then
  NODE_VER=$(node --version 2>&1)
  echo "  ✔ Node $NODE_VER"
else
  echo "  ✗ Node no encontrado. Instalalo primero (ver README)."
  exit 1
fi

# Docker
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  echo "  ✔ Docker OK"
else
  echo "  ✗ Docker no está corriendo. Iniciá Docker Desktop y activá WSL integration."
  exit 1
fi

# docker compose
if docker compose version &>/dev/null 2>&1; then
  echo "  ✔ Docker Compose OK"
else
  echo "  ✗ Docker Compose no encontrado."
  exit 1
fi

# Ollama
if curl -s http://localhost:11434/api/tags &>/dev/null; then
  echo "  ✔ Ollama OK"
else
  echo "  ⚠ Ollama no responde en localhost:11434"
  echo "    Instalalo desde https://ollama.com y asegurate de que esté corriendo."
  echo "    Continuando sin Ollama — vas a necesitarlo para el pipeline AI."
  WARNINGS=$((WARNINGS+1))
fi

# Check we're in repo root
if [ ! -f "pyproject.toml" ] || [ ! -f "docker-compose.yml" ]; then
  echo "  ✗ No estás en la raíz del repo Scouter."
  echo "    Ejecutá: cd ~/src/Scouter && bash scripts/init.sh"
  exit 1
fi

echo ""

# ── 1. Python venv + dependencias ───────────────────────────────────
echo "→ Creando entorno Python..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "  ✔ venv creado"
else
  echo "  ✔ venv ya existe"
fi
.venv/bin/pip install -q --upgrade pip 2>&1 | tail -1
.venv/bin/pip install -q -e ".[dev]" 2>&1 | tail -1
echo "  ✔ Dependencias Python instaladas"

# ── 2. Node dependencias ────────────────────────────────────────────
echo "→ Instalando dependencias Node..."
cd dashboard && npm install --silent 2>&1 | tail -1 && cd ..
echo "  ✔ node_modules instalado"

# ── 3. Archivo .env ─────────────────────────────────────────────────
if [ -f .env ]; then
  echo "→ .env ya existe, no se sobreescribe"
else
  if [ -f .env.example ]; then
    cp .env.example .env
    # Generate a random SECRET_KEY
    RANDOM_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))" 2>/dev/null || echo "cambiar-a-una-clave-random")
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$RANDOM_KEY|" .env 2>/dev/null
    echo "  ✔ .env creado desde .env.example con SECRET_KEY random"
  else
    echo "  ✗ No se encontró .env.example — creá .env manualmente"
    ERRORS=$((ERRORS+1))
  fi
  echo "  ⚠ IMPORTANTE: editá POSTGRES_PASSWORD y las API keys que necesites"
  WARNINGS=$((WARNINGS+1))
fi

# ── 4. Docker infra ─────────────────────────────────────────────────
echo "→ Levantando Postgres + Redis..."
docker compose up -d postgres redis 2>&1 | tail -2

echo "→ Esperando Postgres..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U scouter &>/dev/null 2>&1; then
    echo "  ✔ Postgres listo"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "  ✗ Postgres no respondió en 30s"
    ERRORS=$((ERRORS+1))
  fi
  sleep 1
done

# ── 5. Migraciones de base de datos ─────────────────────────────────
echo "→ Corriendo migraciones Alembic..."
.venv/bin/alembic upgrade head 2>&1 | tail -3
echo "  ✔ Migraciones aplicadas"

# ── 6. Modelos Ollama ───────────────────────────────────────────────
if curl -s http://localhost:11434/api/tags &>/dev/null; then
  echo "→ Verificando modelos Ollama..."
  MODELS_NEEDED=("qwen3.5:4b" "qwen3.5:9b" "qwen3.5:27b" "hermes3:8b")
  INSTALLED=$(curl -s http://localhost:11434/api/tags | python3 -c "
import sys,json
try:
    models = [m['name'] for m in json.load(sys.stdin).get('models',[])]
    print(' '.join(models))
except: pass
" 2>/dev/null)

  for model in "${MODELS_NEEDED[@]}"; do
    if echo "$INSTALLED" | grep -q "$model"; then
      echo "  ✔ $model ya instalado"
    else
      echo "  → Descargando $model (esto puede tardar)..."
      ollama pull "$model" 2>&1 | tail -1
      echo "  ✔ $model descargado"
    fi
  done
else
  echo "→ Ollama no disponible — skipping model downloads"
  echo "  Cuando instales Ollama, ejecutá:"
  echo "    ollama pull qwen3.5:4b"
  echo "    ollama pull qwen3.5:9b"
  echo "    ollama pull qwen3.5:27b"
  echo "    ollama pull hermes3:8b"
  WARNINGS=$((WARNINGS+1))
fi

# ── 7. Crear directorios necesarios ─────────────────────────────────
mkdir -p storage logs .dev-runtime
echo "  ✔ Directorios de runtime creados"

# ── 8. Verificación final ───────────────────────────────────────────
echo ""
echo "→ Verificación final..."

[ -f .env ] && echo "  ✔ .env" || echo "  ✗ .env"
[ -d .venv ] && echo "  ✔ Python venv" || echo "  ✗ Python venv"
[ -d dashboard/node_modules ] && echo "  ✔ node_modules" || echo "  ✗ node_modules"
docker compose exec -T postgres pg_isready -U scouter &>/dev/null 2>&1 && echo "  ✔ Postgres" || echo "  ✗ Postgres"
docker compose exec -T redis redis-cli ping &>/dev/null 2>&1 && echo "  ✔ Redis" || echo "  ✗ Redis"
curl -s http://localhost:11434/api/tags &>/dev/null && echo "  ✔ Ollama" || echo "  ⚠ Ollama no disponible"

# Check DB has tables
CONTAINER=$(docker ps --format '{{.Names}}' | grep postgres | head -1)
TABLE_COUNT=$(docker exec "$CONTAINER" psql -U scouter -d scouter -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')
echo "  ✔ Base de datos: $TABLE_COUNT tablas"

echo ""
echo "════════════════════════════════════════"
if [ "$ERRORS" -eq 0 ]; then
  echo "✔ Init completo."
  if [ "$WARNINGS" -gt 0 ]; then
    echo "  ($WARNINGS advertencias — revisá los items con ⚠)"
  fi
  echo ""
  echo "Para levantar todo:"
  echo "  make up"
  echo ""
  echo "Después verificá:"
  echo "  make status"
  echo "  curl http://localhost:8000/health/detailed"
  echo ""
  echo "Dashboard: http://localhost:3000"
  echo "API docs:  http://localhost:8000/docs"
else
  echo "✗ Init terminó con $ERRORS errores."
  echo "  Revisá los items marcados con ✗ arriba."
fi
echo "════════════════════════════════════════"
