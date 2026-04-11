#!/usr/bin/env bash
# ============================================================================
# Scouter env-backup — snapshot the current .env before any operation that
# might touch it (cp from .env.example, git clean, editor crash, etc.).
#
# Keeps the 10 most recent backups and silently rotates older ones.
#
# Usage:
#   scripts/env-backup.sh                # create a timestamped backup
#   make env-backup                      # same, via Makefile target
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f .env ]; then
  echo "no .env to backup" >&2
  exit 0
fi

TS="$(date +%Y%m%d-%H%M%S)"
DEST=".env.backup.${TS}"
cp .env "$DEST"
chmod 600 "$DEST"
echo "→ backed up .env to ${DEST}"

# Retention: keep only the 10 most recent backups. `ls -1t` sorts by mtime
# descending, `tail -n +11` drops the newest 10 and passes the rest to rm.
ls -1t .env.backup.* 2>/dev/null | tail -n +11 | while IFS= read -r old; do
  rm -f "$old"
  echo "  · rotated out ${old}"
done
