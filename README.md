# ClawScout

Private lead prospecting system for web development services.
Detects businesses that need web development or redesign, enriches leads, scores them,
runs AI-assisted research and outreach flows, and supports human-in-the-loop review before sending.

- Human operators and developers: start with this file, then see [docs/README.md](docs/README.md).
- AI coding agents: start with [AGENTS.md](AGENTS.md).
- Frontend-only work: see [dashboard/README.md](dashboard/README.md) after this file.

## Repo Snapshot

| Metric | Current value |
| --- | --- |
| Backend Python | 203 files / 24,357 LOC |
| Frontend TS/TSX | 100 files / 16,803 LOC |
| Tests | 35 Python files / 237 passing |
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

## Service Map

| Service | Port | Description |
| --- | --- | --- |
| API | `:8000` | FastAPI backend (Swagger at `/docs`, metrics at `/metrics`) |
| Dashboard | `:3000` | Next.js frontend |
| Flower | `:5555` | Celery monitoring dashboard |
| PostgreSQL | `:5432` | Primary database (bound to `127.0.0.1`) |
| Redis | `:6379` | Celery broker + cache |
| Worker | — | Celery worker (`default`, `enrichment`, `scoring`, `llm`, `reviewer`, `research`) + embedded beat scheduler |

---

## Installation from Scratch

> Everything runs inside **WSL** (Windows Subsystem for Linux). The repo **must** live
> in the WSL filesystem (e.g. `~/src/ClawScout`), **not** in `/mnt/c/...` — running
> from the Windows filesystem is significantly slower.

### 1. Install WSL2 + Ubuntu

Open **PowerShell as Administrator**:

```powershell
wsl --install -d Ubuntu
```

Restart your machine if prompted. After restart, open **Ubuntu** from the Start menu and create your Linux user. Then:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git
```

### 2. Install Docker Desktop

1. Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. During setup, make sure **"Use WSL 2 based engine"** is checked
3. After install: Docker Desktop → Settings → Resources → WSL Integration
4. Enable integration with your **Ubuntu** distro
5. Click **Apply & Restart**

Verify from a WSL terminal:

```bash
docker --version
docker compose version
```

### 3. Install Ollama

Install Ollama on the **Windows side** (it uses your GPU directly):

1. Download and install from [ollama.com](https://ollama.com/download)
2. Ollama runs as a service on `localhost:11434` — WSL can reach it automatically

Verify from a WSL terminal:

```bash
curl -s http://localhost:11434/api/tags | head -c 100
```

### 4. Install Python 3.12+ and Node.js v24+

Inside your WSL Ubuntu terminal:

```bash
# Python (check if already installed)
python3 --version

# If not installed or too old:
sudo apt install -y python3 python3-pip python3-venv

# Node.js v24 via nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 24
nvm use 24
```

### 5. Clone and Set Up the Project

```bash
# Clone the repo inside WSL (NOT in /mnt/c/)
cd ~
mkdir -p src && cd src
git clone https://github.com/BriarDevv/ClawScout.git
cd ClawScout

# Configure environment
cp .env.example .env                     # Edit with your values: nano .env

# Python backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start infrastructure (needed for migrations)
docker compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Dashboard
cd dashboard && npm ci && cd ..

# Pull Ollama models (requires Ollama running)
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
ollama pull hermes3:8b

# Make management script executable
chmod +x scripts/clawscout.sh
```

For the full WSL workflow and troubleshooting guide, see
[docs/operations/local-dev-wsl.md](docs/operations/local-dev-wsl.md).

---

## Daily Usage

### Start

```bash
cd ~/src/ClawScout
make up                                  # Starts everything: Postgres, Redis, API, Worker, Dashboard
```

### Stop

```bash
make down                                # Stops everything (preserves Postgres/Redis data)
```

### Check Status

```bash
make status                              # Shows what is running and on which port
```

### Logs

```bash
make logs                                # All logs live (Ctrl+C to exit)
./scripts/clawscout.sh logs api          # API only
./scripts/clawscout.sh logs worker       # Celery worker only
./scripts/clawscout.sh logs dashboard    # Dashboard only
```

### All Commands

| Command | Shortcut | What it does |
| --- | --- | --- |
| `make up` | `./scripts/clawscout.sh start` | Start everything |
| `make down` | `./scripts/clawscout.sh stop` | Stop everything (preserves data) |
| `make restart` | `./scripts/clawscout.sh restart` | Stop + start |
| `make status` | `./scripts/clawscout.sh status` | Show status of each service |
| `make logs` | `./scripts/clawscout.sh logs` | Live logs |
| `make preflight` | `./scripts/clawscout.sh preflight` | Verify configuration |
| `make seed` | `./scripts/clawscout.sh seed` | Load sample data |
| `make test` | `pytest -q` | Run backend tests |
| `make migrate` | `alembic upgrade head` | Run pending database migrations |
| `make nuke` | `./scripts/clawscout.sh nuke` | Stop + delete all data (asks for confirmation) |

### API + Dashboard Only (no Docker or Celery)

If Postgres and Redis are already running and you don't need the worker:

```bash
make dev-up                              # Starts only API :8000 + Dashboard :3000
make dev-down                            # Stops API + Dashboard
make dev-status                          # Status of API + Dashboard
```

### Available Services (when running)

| Service | URL |
| --- | --- |
| Dashboard | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Detailed Health | http://localhost:8000/health/detailed |
| Metrics | http://localhost:8000/metrics |
| Flower (optional) | http://localhost:5555 |

### Manual Mode (4 terminals)

If you prefer individual control over each process:

```bash
# Terminal 1 — Infrastructure
docker compose up postgres redis

# Terminal 2 — API
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — Worker
source .venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info

# Terminal 4 — Dashboard
cd dashboard && npm run dev
```

To stop: `Ctrl+C` in each terminal + `docker compose down`.

### Full Docker Compose (alternative)

```bash
docker compose up -d                     # Start everything in containers
docker compose logs -f                   # View logs
docker compose down                      # Stop
```

---

## Migration / Backup

Export the full environment (DB, secrets, configs) to move ClawScout to another machine:

```bash
# On the current machine
bash scripts/export.sh

# Copy the export ZIP (or folder) to the new machine, then:
bash scripts/import.sh /path/to/clawscout-export-YYYYMMDD-HHMM.zip

# Download Ollama models (listed by import.sh)
ollama pull qwen3.5:4b && ollama pull qwen3.5:9b
ollama pull qwen3.5:27b && ollama pull hermes3:8b

make up  # done
```

The export includes `.env` (secrets/keys), full Postgres dump (leads, chats, briefs, credentials, settings — everything), storage artifacts, and Claude/OMC configs. `export.sh` now leaves both the export folder and a ready-to-move ZIP. Ollama models (~15 GB) are listed but downloaded separately.

**Important:** never regenerate `SECRET_KEY` after importing a DB — credentials are encrypted with it.

| Script / command | When to use it | What it does |
| --- | --- | --- |
| `scripts/init.sh` | First setup | Bootstraps the local environment from scratch |
| `scripts/export.sh` | Migration / backup | Packages `.env`, DB, storage, and configs |
| `scripts/import.sh` | New machine restore | Restores a full exported environment |

---

## LLM Configuration

The system uses Ollama with models assigned by role:

| Role | Default Model | Environment Variable | Purpose |
| --- | --- | --- | --- |
| LEADER | `qwen3.5:4b` | `OLLAMA_LEADER_MODEL` | Internal orchestration and summaries |
| EXECUTOR | `qwen3.5:9b` | `OLLAMA_EXECUTOR_MODEL` | Classification, drafts, scoring, dossiers, briefs |
| REVIEWER | `qwen3.5:27b` | `OLLAMA_REVIEWER_MODEL` | Quality review and async brief validation |
| AGENT | `hermes3:8b` | — | Mote interactive chat agent |

```bash
# Download required models
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
ollama pull hermes3:8b
```

The supported model catalog is configured via `OLLAMA_SUPPORTED_MODELS` in `.env`.
The legacy `OLLAMA_MODEL` variable still works as a fallback for the executor role.

---

## Pipeline

```text
Lead ingestion (Google Maps crawler by territory)
  → Dedup (SHA-256)
  → Enrichment (website analysis, email extraction, signals)
  → Scoring (rules-based, 0-100)
  → LLM Analysis (summary + quality evaluation)
  → IF quality == HIGH:
       → Research (website deep analysis, metadata, signals)
       → Dossier generation (LLM structured report)
       → Commercial Brief (budget, opportunity, contact recommendation)
       → Brief Review (REVIEWER validation)
  → Draft Generation (email + WhatsApp, conditioned on brief)
  → Human Approval → Send
  → Inbound Reply Loop (IMAP sync, classification, reply assistant)
```

### Runtime Modes

| Mode | Behavior |
| --- | --- |
| `safe` | Everything requires manual approval |
| `assisted` | Pipeline runs automatically, send still requires approval |
| `auto` | Full automation including auto-approve and auto-send |

---

## What Is Automatic vs Manual

| Component | Automatic? | How to control |
| --- | --- | --- |
| Crawlers | No — run manually | Nothing to turn off |
| Enrichment / Scoring / Drafts | No — triggered via API | Nothing to turn off |
| Reviewer (27b model) | No — you request it | Nothing to turn off |
| Reply assistant | Toggle in Settings | `reply_assistant_enabled` |
| Auto-classify inbound | Toggle in Settings | `auto_classify_inbound` |
| Automatic reviewer | Toggle in Settings | `reviewer_enabled` |
| Mail inbound sync | Toggle in Settings | `mail_inbound_sync_enabled` |
| WhatsApp alerts | Toggle in Settings | `whatsapp_alerts_enabled` |

Ollama models (4b, 9b, 27b) only consume VRAM when in use. Ollama automatically unloads them from memory after a few minutes of inactivity.

### Disabling AI Features Without Stopping the System

From the dashboard under **Settings > Rules**, you can disable:
- **Reply assistant** — auto-generates responses to inbound emails
- **Reviewer** — automatically reviews drafts and messages
- **Auto-classify inbound** — classifies inbound emails with AI

All these toggles default to `false`, so automatic AI features don't run unless you explicitly enable them.

---

## Project Structure

```
ClawScout/
├── app/                      # Python backend
│   ├── agent/tools/          # 55 Mote tool surfaces for chat-driven operations
│   ├── api/v1/               # FastAPI endpoints and webhooks
│   ├── api/v1/settings/      # Settings split by concern
│   ├── core/                 # Config (pydantic-settings), crypto, logging (structlog)
│   ├── crawlers/             # Google Maps crawling
│   ├── db/                   # Session factory, Base model
│   ├── llm/                  # LLM client, contracts, prompt registry, routing
│   ├── llm/invocations/      # Domain-split AI invocation functions
│   ├── mail/                 # SMTP / IMAP providers
│   ├── models/               # SQLAlchemy ORM models
│   ├── outreach/             # LLM-powered draft generation
│   ├── schemas/              # Pydantic request/response schemas
│   ├── scoring/              # Rule-based scoring engine
│   ├── services/             # 9 subdomains: leads / outreach / inbox / pipeline / research / notifications / settings / comms / dashboard_svc
│   ├── workers/              # Domain-split Celery tasks: pipeline / review / research / crawl / batch / brief
│   └── workflows/            # Explicit orchestration: batch / territory_crawl / outreach_draft / lead_pipeline
├── dashboard/                # Next.js 16 frontend
│   ├── app/                  # App Router — pages
│   ├── components/           # UI, shared, charts, layout
│   ├── lib/                  # API client, hooks, constants
│   ├── data/                 # Mock data for development
│   └── types/                # TypeScript definitions
├── alembic/                  # Database migrations (38 versions)
├── docs/                     # Canonical architecture, plans, operations, product, archive
├── infra/                    # Dockerfiles, infra config
├── scripts/                  # CLI and local operations helpers
├── tests/                    # Backend test suite (35 files)
├── docker-compose.yml        # Service orchestration
├── pyproject.toml            # Python project config
└── .env.example              # Environment variable template
```

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

## API Endpoints

Interactive Swagger docs at `http://localhost:8000/docs`.

| Router | Prefix | Description |
| --- | --- | --- |
| health | `/health` | Health check and detailed health |
| leads | `/api/v1/leads` | CRUD, filters, export, bulk operations |
| enrichment | `/api/v1/enrichment` | Sync and async lead enrichment |
| scoring | `/api/v1/scoring` | Score, LLM analysis, full pipeline |
| outreach | `/api/v1/outreach` | Draft generation, listing, approval |
| suppression | `/api/v1/suppression` | Suppression list management |
| chat | `/api/v1/chat` | Mote agent chat sessions |
| briefs | `/api/v1/briefs` | Commercial brief CRUD and review |
| crawl | `/api/v1/crawl` | Territory crawl triggers |
| dashboard | `/api/v1/dashboard` | Dashboard aggregations and stats |
| leader | `/api/v1/leader` | Leader orchestration commands |
| mail | `/api/v1/mail` | Mail credentials and inbound sync |
| notifications | `/api/v1/notifications` | Notification management |
| performance | `/api/v1/performance` | Analytics and conversion metrics |
| pipelines | `/api/v1/pipelines` | Pipeline orchestration |
| replies | `/api/v1/replies` | Reply assistant review and actions |
| reviews | `/api/v1/reviews` | Draft and brief reviews |
| settings | `/api/v1/settings` | Operational settings (split by concern) |
| tasks | `/api/v1/tasks` | Task tracking and monitoring |
| territories | `/api/v1/territories` | Territory CRUD and assignment |
| telegram | `/api/v1/telegram` | Telegram webhook integration |
| whatsapp | `/api/v1/whatsapp` | WhatsApp alerts and messaging |

## Tests

```bash
# Backend (pytest with SQLite)
pytest -v

# Frontend (type checking)
cd dashboard && npx tsc --noEmit
```

Backend tests use SQLite via an override in `conftest.py` for isolation.

## Environment Variables

Copy `.env.example` to `.env` and fill in the values.
See `.env.example` for the full list of available variables.

## Design Decisions

- **Celery over RQ**: Native retries, queue-based routing, per-task rate limiting, Flower monitoring.
- **Sync SQLAlchemy for v1**: Simpler; FastAPI supports it fine. Async migration is straightforward with SQLAlchemy 2.x.
- **structlog**: Structured JSON logs for auditing and debugging.
- **Dedup via hash**: SHA-256 of normalized (business_name + city + domain). Prevents duplicates at insert time.
- **Global suppression list**: Checked at lead creation, before outreach generation, and on bulk operations.
- **LLM output treated as untrusted**: JSON extraction with fallback; all outputs sanitized before storage.
- **No auto-send in v1**: All outreach requires human approval.
- **shadcn/ui with base-ui**: Uses `render` prop instead of `asChild` (not Radix).
- **Tailwind v4**: Inline config with `@theme` blocks, no `tailwind.config.ts`.

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
