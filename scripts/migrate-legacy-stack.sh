#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[legacy-migrate] %s\n' "$*"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CURRENT_PROJECT="$(basename "$REPO_ROOT" | tr '[:upper:]' '[:lower:]')"
LEGACY_PROJECT="$(printf '%s%s' 'claw' 'scout')"

LEGACY_POSTGRES_CONTAINER="${LEGACY_PROJECT}-postgres-1"
LEGACY_REDIS_CONTAINER="${LEGACY_PROJECT}-redis-1"
CURRENT_PG_VOLUME="${CURRENT_PROJECT}_pgdata"
CURRENT_REDIS_VOLUME="${CURRENT_PROJECT}_redisdata"
LEGACY_PG_VOLUME="${LEGACY_PROJECT}_pgdata"
LEGACY_REDIS_VOLUME="${LEGACY_PROJECT}_redisdata"

container_exists() {
  docker container inspect "$1" >/dev/null 2>&1
}

volume_exists() {
  docker volume inspect "$1" >/dev/null 2>&1
}

copy_volume_if_needed() {
  local from_volume="$1"
  local to_volume="$2"
  local label="$3"

  if ! volume_exists "$from_volume"; then
    return 0
  fi

  if volume_exists "$to_volume"; then
    log "Volumen $label ya preparado en $to_volume"
    return 0
  fi

  log "Migrando volumen legado $from_volume -> $to_volume"
  docker volume create "$to_volume" >/dev/null
  docker run --rm \
    -v "$from_volume:/from" \
    -v "$to_volume:/to" \
    alpine:3.20 \
    sh -c 'cd /from && cp -a . /to'
}

remove_legacy_container_if_present() {
  local container_name="$1"
  if container_exists "$container_name"; then
    log "Removiendo contenedor legado $container_name"
    docker rm -f "$container_name" >/dev/null
  fi
}

remove_legacy_container_if_present "$LEGACY_POSTGRES_CONTAINER"
remove_legacy_container_if_present "$LEGACY_REDIS_CONTAINER"

copy_volume_if_needed "$LEGACY_PG_VOLUME" "$CURRENT_PG_VOLUME" "Postgres"
copy_volume_if_needed "$LEGACY_REDIS_VOLUME" "$CURRENT_REDIS_VOLUME" "Redis"
