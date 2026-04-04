SHELL := /usr/bin/env bash

.PHONY: up down restart status logs preflight seed nuke dev-up dev-down dev-status test migrate

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
test:
	.venv/bin/python -m pytest -v

migrate:
	.venv/bin/python -m alembic upgrade head

# ─── Solo API + Dashboard (sin Docker ni Celery) ──────────────────────────
dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

dev-status:
	bash scripts/dev-status.sh
