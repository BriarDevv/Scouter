# ClawScout

ClawScout is a modular-monolith lead prospecting platform.
It crawls businesses, enriches and scores leads, runs AI-assisted research and outreach flows,
and exposes an operational dashboard for human-in-the-loop execution.

## Start Here

- Human operators and developers: start with this file, then see [docs/README.md](docs/README.md).
- AI coding agents: start with [AGENTS.md](AGENTS.md).
- Frontend-only work: see [dashboard/README.md](dashboard/README.md) after this file.

## Repo Snapshot

| Metric | Current value |
| --- | --- |
| Backend Python | 203 files / 24,357 LOC |
| Frontend TS/TSX | 100 files / 16,803 LOC |
| Tests | 37 Python files / 237 passing |
| Alembic migrations | 38 |
| Agent tools (Mote) | 55 |
| Dashboard pages | 15 |
| Services | 37 services in 9 subdomains |
| Total LOC | ~54,000 (backend + frontend + tests + docs) |

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.x, Celery 5.4+, structlog |
| Database | PostgreSQL 16, Redis 7 |
| AI | Ollama — qwen3.5:4b, qwen3.5:9b, qwen3.5:27b, hermes3:8b |
| Frontend | Next.js 16 App Router, TypeScript strict, Tailwind CSS v4, shadcn/ui (base-ui) |
| Infra | Docker Compose, Alembic, Prometheus metrics |

## LLM Roles

| Role | Model | Purpose |
| --- | --- | --- |
| LEADER | qwen3.5:4b | Internal orchestration and summaries |
| EXECUTOR | qwen3.5:9b | Classification, drafts, scoring, dossiers, briefs |
| REVIEWER | qwen3.5:27b | Quality review and async brief validation |
| AGENT | hermes3:8b | Mote interactive chat agent |

## Pipeline (HIGH leads)

```text
Lead ingestion (Google Maps crawler by territory)
  -> Dedup (SHA-256)
  -> Enrichment (website analysis, email extraction, signals)
  -> Scoring (rules-based, 0-100)
  -> LLM Analysis (summary + quality evaluation)
  -> IF quality == HIGH:
       -> Research (website deep analysis, metadata, signals)
       -> Dossier generation (LLM structured report)
       -> Commercial Brief (budget, opportunity, contact recommendation)
       -> Brief Review (REVIEWER validation)
  -> Draft Generation (email + WhatsApp, conditioned on brief)
  -> Human Approval -> Send
  -> Inbound Reply Loop (IMAP sync, classification, reply assistant)
```

## Runtime Modes

| Mode | Behavior |
| --- | --- |
| `safe` | Everything requires manual approval |
| `assisted` | Pipeline runs automatically, send still requires approval |
| `auto` | Full automation including auto-approve and auto-send |

## Quickstart

ClawScout is designed to run from the Linux side of WSL, not from `/mnt/c/...`.
For the full WSL workflow and troubleshooting guide, see
[docs/operations/local-dev-wsl.md](docs/operations/local-dev-wsl.md).

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cd dashboard
npm ci
cd ..
```

### 2. Configure the environment

```bash
cp .env.example .env
```

Fill in the required values before starting the stack.

### 3. Start infrastructure and migrate the database

```bash
docker compose up -d postgres redis
alembic upgrade head
```

### 4. Start the app

```bash
make up
```

### 5. Verify the main surfaces

```bash
make status
curl http://localhost:8000/health
curl http://localhost:8000/docs
curl http://localhost:8000/metrics
```

## Common Commands

| Command | Purpose |
| --- | --- |
| `make up` | Start the local stack |
| `make down` | Stop the local stack |
| `make status` | Show service status |
| `make logs` | Tail logs |
| `make preflight` | Run operational checks |
| `pytest -q` | Run backend tests |
| `cd dashboard && npx tsc --noEmit` | Type-check the frontend |

## Scripts

| Script / command | When to use it | What it does |
| --- | --- | --- |
| `scripts/init.sh` | First setup | Bootstraps the local environment from scratch |
| `scripts/export.sh` | Migration / backup | Packages `.env`, DB, storage, and configs |
| `scripts/import.sh` | New machine restore | Restores a full exported environment |
| `make up` | Everyday | Starts the full local stack |
| `make down` | Everyday | Stops the stack |
| `make status` | Everyday | Shows service status |

## Dashboard (15 pages)

| Page | Route | Description |
| --- | --- | --- |
| Mote Chat | `/` | Full-page chat with the AI agent |
| Panel | `/panel` | Operational dashboard with stats, controls, and health |
| Leads | `/leads` | Lead list with filters and exports |
| Lead Detail | `/leads/[id]` | Dossier, brief, drafts, replies, and timeline |
| Dossiers | `/dossiers` | Completed investigations for HIGH leads |
| Briefs | `/briefs` | Commercial briefs with budget/opportunity |
| Outreach | `/outreach` | Draft approval and sending |
| Responses | `/responses` | Inbound mail, classification, and reply assistant |
| Performance | `/performance` | Conversion and operational analytics |
| Map | `/map` | Leaflet map with leads, territories, and heatmap |
| Suppression | `/suppression` | Suppression list management |
| Notifications | `/notifications` | Notification center |
| Security | `/security` | Security alerts |
| Activity | `/activity` | Real-time task and pipeline monitor |
| Settings | `/settings` | Multi-tab operational configuration |

## Repo Map

| Path | Purpose |
| --- | --- |
| `app/agent/tools/` | 55 Mote tool surfaces for chat-driven operations |
| `app/api/v1/` | REST endpoints and webhooks |
| `app/api/v1/settings/` | Settings split by concern |
| `app/core/` | Config, crypto, logging |
| `app/crawlers/` | Google Maps crawling |
| `app/db/` | SQLAlchemy session and engine |
| `app/llm/` | LLM client, contracts, prompt registry, routing |
| `app/llm/invocations/` | Domain-split AI invocation functions |
| `app/mail/` | SMTP and IMAP providers |
| `app/models/` | SQLAlchemy ORM models |
| `app/outreach/` | Draft generators |
| `app/schemas/` | Pydantic DTOs |
| `app/scoring/` | Lead scoring rules |
| `app/services/` | 9 service subdomains plus a small transversal layer |
| `app/workers/` | Domain-split Celery task modules |
| `app/workflows/` | Explicit orchestration workflows |
| `dashboard/` | Next.js operational frontend |
| `docs/` | Canonical architecture, plans, operations, product, archive |
| `scripts/` | CLI and local operations helpers |
| `tests/` | Backend test suite |
| `alembic/` | Database migrations |

## Backend Structure

```text
app/
  agent/tools/          # Mote tools
  api/v1/               # REST endpoints
  api/v1/settings/      # settings split by concern
  core/                 # config, crypto, logging
  crawlers/             # Google Maps crawler
  db/                   # SQLAlchemy session
  llm/                  # LLM client + structured outputs
  llm/invocations/      # lead / outreach / reply / research invocations
  mail/                 # SMTP / IMAP providers
  models/               # SQLAlchemy models
  outreach/             # draft generators
  schemas/              # Pydantic DTOs
  scoring/              # scoring rules
  services/             # leads / outreach / inbox / pipeline / research / notifications / settings / comms / dashboard_svc
  workers/              # pipeline / review / research / crawl / batch / brief tasks
  workflows/            # batch / territory_crawl / outreach_draft / lead_pipeline
```

## Docker Services

| Service | Port | Description |
| --- | --- | --- |
| API | `:8000` | FastAPI backend (`/docs`, `/metrics`) |
| Dashboard | `:3000` | Next.js frontend |
| PostgreSQL | `:5432` | Primary database (bound to `127.0.0.1`) |
| Redis | `:6379` | Celery broker + cache |
| Worker | — | Celery worker (`default`, `enrichment`, `scoring`, `llm`, `reviewer`, `research`) |
| Beat | — | Celery beat scheduler (janitor every 5 minutes) |

## Read Next

| If you want to... | Read this next |
| --- | --- |
| Understand the documentation map | [docs/README.md](docs/README.md) |
| Work on the repo with an AI assistant | [AGENTS.md](AGENTS.md) |
| Understand the current architecture | [docs/architecture/audit.md](docs/architecture/audit.md) |
| See the target architecture | [docs/architecture/target.md](docs/architecture/target.md) |
| Follow the current refactor sequence | [docs/plans/refactor-roadmap.md](docs/plans/refactor-roadmap.md) |
| Run the stack reliably in WSL | [docs/operations/local-dev-wsl.md](docs/operations/local-dev-wsl.md) |
| Understand product intent and positioning | [docs/product/proposal.md](docs/product/proposal.md) |
| Work only on the dashboard | [dashboard/README.md](dashboard/README.md) |

## Notes

- [SOUL.md](SOUL.md) and [IDENTITY.md](IDENTITY.md) are runtime assets for the Mote agent.
  They are not the main repo entrypoint for humans.
- Historical audits, reports, and old plans live under `docs/archive/`.
  They are useful context, not the canonical source of truth.
