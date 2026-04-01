# ClawScout

Private lead prospecting system for web development services.
Python 3.12+ / FastAPI backend, Next.js 16 frontend, Hermes agent system.

## Architecture

```
app/                        Python backend (FastAPI)
  agent/                    Hermes 3 agentic chat (SSE streaming, tool execution)
    core.py                   Agent loop: run_agent_turn() streams LLM + executes tools
    hermes_format.py          Parses <tool_call> XML from Hermes 3 models
    channel_router.py         Routes agent to Telegram / WhatsApp channels
    prompts.py                Builds system prompt from SOUL.md + IDENTITY.md
    tools/                    14 tool modules (search_leads, list_drafts, etc.)
  api/v1/                   REST endpoints (leads, chat, crawl, outreach, settings, mail, etc.)
  core/                     Config (Pydantic Settings), crypto, structlog logging
  crawlers/                 Google Maps crawler (base_crawler + google_maps_crawler)
  db/                       SQLAlchemy engine/session (sync, get_session dependency)
  llm/                      LLM client with role-based routing (leader/executor/reviewer)
    catalog.py                Model catalog and aliases
    resolver.py               Role -> model resolution
    prompts.py                Prompt templates for classification, drafts, scoring
  mail/                     SMTP send + IMAP ingest providers
  models/                   SQLAlchemy ORM (UUID PKs, all exported in __init__.py)
  outreach/                 Outreach message generator
  schemas/                  Pydantic v2 schemas (XxxCreate / XxxUpdate / XxxResponse)
  scoring/                  Lead scoring engine (55pt signals, 15pt industry bonus)
  services/                 Stateless business logic (fn(db: Session, ...) pattern)
  workers/                  Celery app, async tasks, janitor cleanup

dashboard/                  Next.js 16 frontend (App Router, TypeScript strict)
  app/                      Pages: leads, map, outreach, settings, activity, etc.
  components/               UI organized by domain (dashboard, leads, map, chat, settings)
    ui/                       shadcn/ui primitives (base-ui, NOT Radix)
  lib/api/client.ts         Centralized API client (all backend calls go through here)
  lib/hooks/                Custom hooks (usePageData, useChatPanel, useChat)
  types/index.ts            All TypeScript interfaces

tests/                      Pytest suite (SQLite override in conftest.py, ~150 tests)
scripts/                    CLI tools (clawscoutctl, browserctl, preflight, seed, dev-up/down)
skills/                     Hermes agent skills (7 modules: actions, briefs, browser, data, mail, notifications, whatsapp)
alembic/                    DB migrations
infra/docker/               Dockerfile
docs/                       Operational docs, security audit, feature specs
```

## LLM Roles

| Role | Default Model | Purpose |
|------|--------------|---------|
| LEADER | qwen3.5:4b | Orchestration, summaries, briefs |
| EXECUTOR | qwen3.5:9b | Classification, draft generation, scoring |
| REVIEWER | qwen3.5:27b | Quality review, second opinions (async) |

Models configured via env vars. Hermes agent uses EXECUTOR by default for chat.

## Key Files

| File | Why it matters |
|------|---------------|
| `SOUL.md` | Agent personality — read by `app/agent/prompts.py` at startup |
| `IDENTITY.md` | Agent identity template — same |
| `app/agent/core.py` | The Hermes agent loop — SSE streaming + tool execution |
| `app/api/v1/` | All REST endpoints — start here for API changes |
| `app/services/` | All business logic — stateless, takes `db: Session` |
| `app/models/__init__.py` | Model registry — new models must be exported here |
| `dashboard/lib/api/client.ts` | Single API client — all frontend calls go through here |
| `dashboard/components/settings/types.ts` | Settings tab registry |
| `tests/conftest.py` | Test DB setup (SQLite override) |
| `Makefile` | `make up`, `make down`, `make status`, `make test` |

## Conventions

**Backend**: Ruff linter (line 100), structlog (event name + kwargs, no f-strings), services are stateless functions, UUID primary keys, enum values lowercase strings.

**Frontend**: Tailwind v4 (`@import "tailwindcss"`), CVA for variants, `cn()` utility, all text in Spanish (es-AR), kebab-case filenames, `"use client"` for interactive components.

**Both**: Dedup hash = SHA-256(business_name + city + domain). No auto-send — all outreach requires human approval.
