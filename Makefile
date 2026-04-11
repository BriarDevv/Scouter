SHELL := /usr/bin/env bash

.PHONY: up down restart status logs preflight seed nuke dev-up dev-down dev-status test test-v lint typecheck migrate

# ─── Stack completo (infra + API + worker + dashboard) ─────────────────────
up:
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

# ─── Solo API + Dashboard (sin Docker ni Celery) ──────────────────────────
dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

dev-status:
	bash scripts/dev-status.sh
