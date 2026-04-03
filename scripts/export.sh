#!/usr/bin/env bash
# ============================================================================
# ClawScout Export — empaqueta todo lo necesario para migrar a otra PC
# Uso: bash scripts/export.sh [carpeta-destino|zip-destino]
# ============================================================================
set -euo pipefail

INPUT_PATH="${1:-clawscout-export-$(date +%Y%m%d-%H%M)}"
if [[ "$INPUT_PATH" == *.zip ]]; then
  ZIP_PATH="$INPUT_PATH"
  EXPORT_DIR="${INPUT_PATH%.zip}"
else
  EXPORT_DIR="$INPUT_PATH"
  ZIP_PATH="${EXPORT_DIR}.zip"
fi

mkdir -p "$EXPORT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║     ClawScout Export                 ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. .env (secrets, API keys, passwords, config) ──────────────────
if [ -f .env ]; then
  cp .env "$EXPORT_DIR/.env"
  echo "✔ .env copiado"
else
  echo "⚠ .env no encontrado — vas a tener que crearlo manualmente"
fi

# ── 2. Postgres dump (leads, chats, briefs, credentials, TODO) ──────
echo "→ Exportando base de datos..."
if docker ps --format '{{.Names}}' | grep -q postgres; then
  CONTAINER=$(docker ps --format '{{.Names}}' | grep postgres | head -1)
  docker exec "$CONTAINER" pg_dump -U clawscout clawscout 2>/dev/null | gzip > "$EXPORT_DIR/db.sql.gz"
  echo "✔ Base de datos exportada ($(du -h "$EXPORT_DIR/db.sql.gz" | cut -f1))"
elif command -v pg_dump &>/dev/null; then
  pg_dump -h 127.0.0.1 -U clawscout clawscout 2>/dev/null | gzip > "$EXPORT_DIR/db.sql.gz"
  echo "✔ Base de datos exportada via pg_dump local"
else
  echo "⚠ No se pudo exportar DB — Postgres no está corriendo"
fi

# ── 3. Storage (artifacts, screenshots) ─────────────────────────────
if [ -d storage ] && [ "$(ls -A storage 2>/dev/null)" ]; then
  tar czf "$EXPORT_DIR/storage.tar.gz" storage/
  echo "✔ Storage exportado ($(du -h "$EXPORT_DIR/storage.tar.gz" | cut -f1))"
else
  echo "– Storage vacío, nada que exportar"
fi

# ── 4. Modelos Ollama ───────────────────────────────────────────────
if curl -s http://localhost:11434/api/tags &>/dev/null; then
  curl -s http://localhost:11434/api/tags > "$EXPORT_DIR/ollama-models.json"
  MODELS=$(python3 -c "import json; data=json.load(open('$EXPORT_DIR/ollama-models.json')); print(len(data.get('models',[])))" 2>/dev/null || echo "?")
  echo "✔ Lista de modelos Ollama guardada ($MODELS modelos)"
else
  echo "⚠ Ollama no está corriendo — no se guardó lista de modelos"
fi

# ── 5. Claude Code config ───────────────────────────────────────────
if [ -d .claude ]; then
  tar czf "$EXPORT_DIR/claude-config.tar.gz" .claude/
  echo "✔ Config Claude Code exportada"
else
  echo "– Sin config de Claude Code"
fi

# ── 6. OMC config ───────────────────────────────────────────────────
if [ -d .omc ]; then
  tar czf "$EXPORT_DIR/omc-config.tar.gz" .omc/ 2>/dev/null
  echo "✔ Config OMC exportada"
else
  echo "– Sin config OMC"
fi

# ── Resumen ─────────────────────────────────────────────────────────
echo "→ Generando ZIP..."
rm -f "$ZIP_PATH"
python3 - "$EXPORT_DIR" "$ZIP_PATH" <<'PY'
import sys
import zipfile
from pathlib import Path

export_dir = Path(sys.argv[1])
zip_path = Path(sys.argv[2])

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(export_dir.rglob("*")):
        if path.is_dir():
            continue
        zf.write(path, path.relative_to(export_dir.parent))
PY
echo "✔ ZIP generado ($(du -h "$ZIP_PATH" | cut -f1))"

echo ""
echo "════════════════════════════════════════"
echo "Export completo en: $EXPORT_DIR/"
echo "ZIP listo en:        $ZIP_PATH"
echo ""
ls -lh "$EXPORT_DIR/"
echo ""
ls -lh "$ZIP_PATH"
echo ""
echo "Próximo paso:"
echo "  1. Copiá '$ZIP_PATH' o la carpeta '$EXPORT_DIR/' a USB/nube"
echo "  2. En la PC nueva: seguí el README para instalar"
echo "  3. Después: bash scripts/import.sh $ZIP_PATH"
echo "════════════════════════════════════════"
