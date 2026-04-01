SHELL := /usr/bin/env bash

.PHONY: up down restart status logs preflight seed nuke dev-up dev-down dev-status test migrate

# ─── Stack completo (infra + API + worker + dashboard) ─────────────────────
up:
	bash scripts/clawscout.sh start

down:
	bash scripts/clawscout.sh stop

restart:
	bash scripts/clawscout.sh restart

status:
	bash scripts/clawscout.sh status

logs:
	bash scripts/clawscout.sh logs

preflight:
	bash scripts/clawscout.sh preflight

seed:
	bash scripts/clawscout.sh seed

nuke:
	bash scripts/clawscout.sh nuke

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
