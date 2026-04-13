SHELL := /usr/bin/env bash

.PHONY: up down restart status logs preflight preflight-secrets seed nuke dev-up dev-down dev-status test test-v lint typecheck migrate env-backup env-restore validate lint-fe typecheck-fe test-fe sync-proxy sync-enums

# ─── Stack completo (infra + API + worker + dashboard) ─────────────────────
up: preflight-secrets
	bash scripts/scouter.sh start

down:
	bash scripts/scouter.sh stop

restart:
	bash scripts/scouter.sh restart

status:
	bash scripts/scouter.sh status

logs:
	bash scripts/scouter.sh logs

preflight:
	bash scripts/scouter.sh preflight

seed:
	bash scripts/scouter.sh seed

nuke:
	bash scripts/scouter.sh nuke

# ─── Test & Migrations ───────────────────────────────────────────────────
# Matches .github/workflows/ci.yml — one canonical command.
test:
	.venv/bin/python -m pytest -x -q --tb=short --cov=app --cov-report=term-missing --cov-fail-under=65

# Verbose variant for interactive development (not used by CI).
test-v:
	.venv/bin/python -m pytest -v

# Lint & typecheck — same commands as CI.
lint:
	.venv/bin/python -m ruff check app/ tests/
	.venv/bin/python -m ruff format --check app/ tests/

typecheck:
	.venv/bin/python -m mypy app/ --ignore-missing-imports

migrate:
	.venv/bin/python -m alembic upgrade head

# ─── Secrets & env file safety ────────────────────────────────────────────
# Fails fast if SECRET_KEY / GOOGLE_MAPS_API_KEY are missing or placeholder,
# or if DB has encrypted rows that won't decrypt with the current key.
preflight-secrets:
	@.venv/bin/python scripts/check_secrets.py

# Timestamped snapshot of .env before any operation that might touch it.
env-backup:
	@bash scripts/env-backup.sh

# List available backups and print restore instructions.
env-restore:
	@echo "Available .env backups (newest first):"
	@ls -1t .env.backup.* 2>/dev/null || echo "  (none)"
	@echo ""
	@echo "To restore one, run:"
	@echo "  cp .env.backup.YYYYMMDD-HHMMSS .env && scripts/scouter.sh restart"

# ─── Solo API + Dashboard (sin Docker ni Celery) ──────────────────────────
dev-up: preflight-secrets
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

dev-status:
	bash scripts/dev-status.sh

# ─── Frontend targets ────────────────────────────────────────────────────
lint-fe:
	cd dashboard && npm run lint

typecheck-fe:
	cd dashboard && npx tsc --noEmit

test-fe:
	cd dashboard && npx vitest run

# ─── Codegen & sync ─────────────────────────────────────────────────────
sync-enums:
	.venv/bin/python scripts/sync-enums.py

sync-proxy:
	.venv/bin/python scripts/sync-proxy-allowlist.py

# ─── Full validation (all checks) ────────────────────────────────────────
validate: preflight-secrets sync-enums lint typecheck test sync-proxy
	cd dashboard && npx tsc --noEmit && npm run lint
