# Scouter

Private lead prospecting system for web development services with an AI Agent OS.

Detects businesses that need web development, enriches leads, scores them, runs AI research and outreach, and manages client conversations — with human-in-the-loop control at every step.

- Human operators and developers: start here, then [docs/README.md](docs/README.md).
- AI coding agents: start with [AGENTS.md](AGENTS.md).
- Frontend-only work: [dashboard/README.md](dashboard/README.md).

## Repo Snapshot

| Metric | Current value |
| --- | --- |
| Backend Python | 221 files |
| Frontend TS/TSX | 108 files |
| Tests | 43 files / 313 passing |
| Alembic migrations | 42 |
| Agent tools (Mote) | 55 |
| Dashboard pages | 17 |
| Services | 37 services in 9 subdomains |
| Agent OS docs | 10 canonical docs |

## AI Agent OS

4 AI roles work as a team through the pipeline:

| Role | Model | What it does |
| --- | --- | --- |
| **Mote** (Agent) | hermes3:8b | Operator chat + WhatsApp client closer |
| **Scout** (Agent) | qwen3.5:9b | Deep web research with Playwright |
| **Executor** (Model) | qwen3.5:9b | Generates analysis, briefs, drafts |
| **Reviewer** (Model) | qwen3.5:27b | Quality gate with structured corrections |

See [docs/agents/hierarchy.md](docs/agents/hierarchy.md) for full team structure.

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.x, Celery 5.4+, structlog |
| Database | PostgreSQL 16, Redis 7 |
| AI | Ollama (local) — 4 models, Kapso (WhatsApp Business Cloud API) |
| Frontend | Next.js 16, TypeScript strict, Tailwind CSS v4, shadcn/ui |
| Infra | Docker Compose, Alembic, Prometheus metrics |

## Quick Start

```bash
git clone https://github.com/BriarDevv/Scouter.git ~/src/Scouter
cd ~/src/Scouter
bash scripts/init.sh    # Sets up everything: venv, deps, DB, models
make up                 # Starts all services
```

Dashboard: http://localhost:3000 (onboarding wizard on first run)
API docs: http://localhost:8000/docs

For detailed installation (WSL, Docker, Ollama), see [docs/operations/install.md](docs/operations/install.md).

## Daily Usage

| Command | What it does |
| --- | --- |
| `make up` | Start everything |
| `make down` | Stop everything |
| `make status` | Show service status |
| `make logs` | Live logs |
| `make test` | Run backend tests |
| `make preflight` | Verify configuration |
| `make migrate` | Run pending DB migrations |

## Pipeline

```
Lead ingestion (Google Maps crawler)
  -> Enrichment (website, email, signals)
  -> Scoring (rules-based, 0-100)
  -> LLM Analysis (quality evaluation)
  -> Scout Research (Playwright deep investigation)
  -> Commercial Brief (budget, opportunity, angle)
  -> Reviewer Validation (structured corrections)
  -> Draft Generation (email + WhatsApp, using full pipeline context)
  -> Template Send (WhatsApp) or Email
  -> Client Conversation (Mote closer mode)
  -> Outcome Tracking (WON/LOST -> scoring recommendations)
```

## Runtime Modes

| Mode | Behavior |
| --- | --- |
| `safe` | Everything requires human approval |
| `assisted` | Pipeline auto, sending requires approval |
| `outreach` | Mote sends template, waits for reply, human takes over |
| `closer` | Mote manages full conversation with clients |

LOW_RESOURCE_MODE available for notebooks without GPU (single queue, concurrency=1). Toggle in Settings > Rules.

## Dashboard Pages

| Page | Route |
| --- | --- |
| Mote Chat | `/` |
| Panel (overview) | `/panel` |
| AI Office | `/ai-office` |
| Leads | `/leads` |
| Lead Detail | `/leads/[id]` |
| Onboarding | `/onboarding` |
| Outreach | `/outreach` |
| Performance | `/performance` |
| Settings | `/settings` |

+8 more pages (briefs, dossiers, responses, map, notifications, security, activity, suppression).

## Project Structure

```
app/                    Python backend
  agent/                Mote agent loop + Scout research agent + tools
  api/v1/               FastAPI endpoints
  llm/                  Model routing, prompts, invocations, contracts
  models/               SQLAlchemy ORM (28 models)
  services/             Business logic (9 subdomains)
  workers/              Celery tasks
  workflows/            Explicit orchestration seams
dashboard/              Next.js frontend
  app/                  Pages (App Router)
  components/           UI components
  lib/                  API client, hooks, constants
docs/                   Canonical docs, agents, architecture, operations
  agents/               Agent OS: hierarchy, protocols, governance, identities
skills/                 7 Mote skills + model routing
tests/                  43 test files, 313 passing
scripts/                CLI and operations helpers
```

## Migration / Backup

```bash
bash scripts/export.sh              # Export DB + secrets + configs to ZIP
bash scripts/import.sh export.zip   # Restore on new machine
```

## Tests

```bash
pytest -v                           # Backend (SQLite isolation)
cd dashboard && npx tsc --noEmit    # Frontend type check
```

## Read Next

| Goal | Read |
| --- | --- |
| Documentation map | [docs/README.md](docs/README.md) |
| AI assistant work | [AGENTS.md](AGENTS.md) |
| Agent OS understanding | [docs/agents/hierarchy.md](docs/agents/hierarchy.md) |
| Full installation guide | [docs/operations/install.md](docs/operations/install.md) |
| WSL workflow | [docs/operations/local-dev-wsl.md](docs/operations/local-dev-wsl.md) |
| Dashboard only | [dashboard/README.md](dashboard/README.md) |
| Product context | [docs/product/proposal.md](docs/product/proposal.md) |
