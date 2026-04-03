#!/usr/bin/env bash
# ============================================================================
# ClawScout Import — restaura un export en una PC nueva
# Prerequisito: seguir el README primero (WSL, Docker, Ollama, Python, Node)
# Uso: bash scripts/import.sh <carpeta-export>
# ============================================================================
set -euo pipefail

IMPORT_DIR="${1:?Uso: bash scripts/import.sh <carpeta-export>}"

if [ ! -d "$IMPORT_DIR" ]; then
  echo "ERROR: No existe la carpeta '$IMPORT_DIR'"
  exit 1
fi

echo "╔══════════════════════════════════════╗"
echo "║     ClawScout Import                 ║"
echo "╚══════════════════════════════════════╝"
echo "Importando desde: $IMPORT_DIR"
echo ""

# ── 1. Restaurar .env ───────────────────────────────────────────────
if [ -f "$IMPORT_DIR/.env" ]; then
  cp "$IMPORT_DIR/.env" .env
  echo "✔ .env restaurado"
else
  echo "⚠ No hay .env en el export — vas a tener que crearlo"
fi

# ── 2. Instalar dependencias Python ─────────────────────────────────
echo "→ Instalando dependencias Python..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -e ".[dev]" 2>&1 | tail -1
echo "✔ Python venv instalado"

# ── 3. Instalar dependencias Node ───────────────────────────────────
echo "→ Instalando dependencias Node..."
cd dashboard && npm install --silent 2>&1 | tail -1 && cd ..
echo "✔ node_modules instalado"

# ── 4. Levantar infra Docker ────────────────────────────────────────
echo "→ Levantando Postgres + Redis..."
docker compose up -d postgres redis 2>&1 | tail -2
echo "→ Esperando que Postgres esté listo..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U clawscout &>/dev/null; then
    break
  fi
  sleep 1
done
echo "✔ Postgres + Redis listos"

# ── 5. Restaurar base de datos ──────────────────────────────────────
if [ -f "$IMPORT_DIR/db.sql.gz" ]; then
  echo "→ Restaurando base de datos..."
  CONTAINER=$(docker ps --format '{{.Names}}' | grep postgres | head -1)
  
  # Dropear y recrear la DB para import limpio
  docker exec "$CONTAINER" psql -U clawscout -d postgres -c "DROP DATABASE IF EXISTS clawscout;" 2>/dev/null
  docker exec "$CONTAINER" psql -U clawscout -d postgres -c "CREATE DATABASE clawscout;" 2>/dev/null
  
  gunzip -c "$IMPORT_DIR/db.sql.gz" | docker exec -i "$CONTAINER" psql -U clawscout -d clawscout -q 2>/dev/null
  echo "✔ Base de datos restaurada (leads, chats, briefs, credentials, settings, todo)"
else
  echo "→ Sin dump de DB — corriendo migraciones desde cero..."
  .venv/bin/alembic upgrade head
  echo "✔ Migraciones aplicadas (DB vacía)"
fi

# ── 6. Restaurar storage ────────────────────────────────────────────
if [ -f "$IMPORT_DIR/storage.tar.gz" ]; then
  tar xzf "$IMPORT_DIR/storage.tar.gz"
  echo "✔ Storage restaurado"
else
  echo "– Sin storage que restaurar"
fi

# ── 7. Restaurar config Claude Code ─────────────────────────────────
if [ -f "$IMPORT_DIR/claude-config.tar.gz" ]; then
  tar xzf "$IMPORT_DIR/claude-config.tar.gz"
  echo "✔ Config Claude Code restaurada"
fi

# ── 8. Restaurar config OMC ─────────────────────────────────────────
if [ -f "$IMPORT_DIR/omc-config.tar.gz" ]; then
  tar xzf "$IMPORT_DIR/omc-config.tar.gz"
  echo "✔ Config OMC restaurada"
fi

# ── 9. Modelos Ollama ───────────────────────────────────────────────
if [ -f "$IMPORT_DIR/ollama-models.json" ]; then
  echo ""
  echo "→ Modelos Ollama necesarios (descargar manualmente):"
  python3 -c "
import json, sys
try:
    data = json.load(open('$IMPORT_DIR/ollama-models.json'))
    for m in data.get('models', []):
        print(f'    ollama pull {m[\"name\"]}')
except Exception:
    print('    (no se pudo leer la lista)')
" 2>/dev/null
  echo ""
  echo "  Ejecutá cada 'ollama pull' de arriba si no tenés los modelos."
fi

# ── 10. Verificación ────────────────────────────────────────────────
echo ""
echo "→ Verificando sistema..."
ERRORS=0

# Check .env
[ -f .env ] && echo "  ✔ .env presente" || { echo "  ✗ .env falta"; ERRORS=$((ERRORS+1)); }

# Check venv
[ -f .venv/bin/python ] && echo "  ✔ Python venv OK" || { echo "  ✗ venv falta"; ERRORS=$((ERRORS+1)); }

# Check node_modules
[ -d dashboard/node_modules ] && echo "  ✔ node_modules OK" || { echo "  ✗ node_modules falta"; ERRORS=$((ERRORS+1)); }

# Check Postgres
docker compose exec -T postgres pg_isready -U clawscout &>/dev/null && echo "  ✔ Postgres OK" || { echo "  ✗ Postgres no responde"; ERRORS=$((ERRORS+1)); }

# Check Redis
docker compose exec -T redis redis-cli ping &>/dev/null && echo "  ✔ Redis OK" || { echo "  ✗ Redis no responde"; ERRORS=$((ERRORS+1)); }

# Check Ollama
curl -s http://localhost:11434/api/tags &>/dev/null && echo "  ✔ Ollama OK" || echo "  ⚠ Ollama no responde (necesitás instalarlo y correr los pulls)"

# Check DB has data
if [ -f "$IMPORT_DIR/db.sql.gz" ]; then
  CONTAINER=$(docker ps --format '{{.Names}}' | grep postgres | head -1)
  LEAD_COUNT=$(docker exec "$CONTAINER" psql -U clawscout -d clawscout -t -c "SELECT count(*) FROM leads;" 2>/dev/null | tr -d ' ')
  echo "  ✔ Base de datos: $LEAD_COUNT leads"
fi

echo ""
if [ "$ERRORS" -eq 0 ]; then
  echo "════════════════════════════════════════"
  echo "✔ Import completo. Tu ClawScout está listo."
  echo ""
  echo "Para levantar todo:"
  echo "  make up"
  echo ""
  echo "Para verificar salud:"
  echo "  make status"
  echo "  curl http://localhost:8000/health/detailed"
  echo "════════════════════════════════════════"
else
  echo "⚠ Import terminó con $ERRORS errores. Revisá los items marcados con ✗."
fi
