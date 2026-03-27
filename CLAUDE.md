# ClawScout

Private lead prospecting system for web development services.
Python 3.12+ / FastAPI backend + Next.js 16 frontend. Runs in WSL2.

## Commands

```bash
make up              # Start full stack (Postgres, Redis, API, Worker, Dashboard)
make down            # Stop everything
make status          # Show running services
pytest -v            # Backend tests (SQLite)
cd dashboard && npx tsc --noEmit   # Frontend type check
python scripts/preflight.py        # Full system health check
```

## Backend Conventions

- **Stack**: FastAPI, SQLAlchemy 2.x (sync), Celery + Redis, structlog, Pydantic 2.x
- **Linter**: Ruff — line length 100, target py312, rules: E/F/W/I/N/UP/B/SIM/S
- **Services**: Stateless functions in `app/services/`, take `db: Session` as first param, raise custom exceptions
- **Models**: UUID primary keys, export all in `app/models/__init__.py`, enum values are lowercase strings
- **Schemas**: `XxxCreate`, `XxxUpdate`, `XxxResponse` naming in `app/schemas/`
- **Endpoints**: Register routers in `app/api/router.py`, always use `Depends(get_session)`
- **Async tasks**: Queue via Celery `.delay()`, track with `queue_task_run()`, return `TaskEnqueueResponse`
- **Logging**: structlog with event name + kwargs — `logger.info("event_name", lead_id=id)` — never f-strings
- **Tests**: SQLite override in `tests/conftest.py`, deterministic, seed data inline

## Frontend Conventions

- **Stack**: Next.js 16 App Router, TypeScript strict, Tailwind CSS v4, React 19
- **UI library**: shadcn/ui with **base-ui** (NOT Radix) — use `render` prop, not `asChild`
- **Styling**: CVA for variants, `cn()` from `lib/utils.ts` (clsx + tailwind-merge)
- **Tailwind v4**: `@import "tailwindcss"` + `@theme inline` in `globals.css` — no `tailwind.config.ts`
- **API calls**: All through `dashboard/lib/api/client.ts` (centralized)
- **Locale**: All user-facing text in Spanish (es-AR)
- **Components**: `"use client"` for interactive, kebab-case filenames

## LLM System

Three roles with dedicated models (configurable via env):

| Role | Default Model | Purpose |
|------|--------------|---------|
| LEADER | `qwen3.5:4b` | Orchestration, summaries, briefs |
| EXECUTOR | `qwen3.5:9b` | Classification, draft generation, scoring |
| REVIEWER | `qwen3.5:27b` | Quality review, second opinions (async) |

- External data wrapped in `<external_data>` tags (prompt injection defense)
- LLM output treated as untrusted — JSON extraction with fallback, sanitized before storage
- Prompts in `app/llm/prompts.py`, role resolution in `app/llm/resolver.py`

## Key Gotchas

- Repo **must** live in WSL filesystem (`~/src/ClawScout`), not `/mnt/c/`
- No auto-send in v1 — all outreach requires human approval
- `celerybeat-schedule` is a binary runtime file (in `.gitignore`)
- OpenClaw workspace files (AGENTS.md, SOUL.md, IDENTITY.md, etc.) are used by `ai_workspace_service.py` — don't delete them
- Dedup hash: SHA-256 of (business_name + city + domain)

## Commit Style

```
type: concise description

Types: feat, fix, chore, docs, refactor, security, build
```
