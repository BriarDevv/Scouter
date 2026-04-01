# ClawScout

Private lead prospecting system for web development services.
Detects businesses that need web development or redesign, enriches leads, scores them, generates outreach drafts, and supports human-in-the-loop review before sending.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.x, Celery, structlog |
| Database | PostgreSQL 16, Redis 7 |
| LLM | Ollama -- catalog: `qwen3.5:4b`, `qwen3.5:9b`, `qwen3.5:27b` |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui (base-ui) |
| Infra | Docker Compose, Alembic (migrations) |

## Service Map

| Service | Port | Description |
|---------|------|-------------|
| API | `:8000` | FastAPI backend (Swagger at `/docs`) |
| Dashboard | `:3000` | Next.js frontend |
| Flower | `:5555` | Celery monitoring dashboard |
| PostgreSQL | `:5432` | Primary database |
| Redis | `:6379` | Celery broker + cache |

---

## Installation from Scratch

> Everything runs inside **WSL** (Windows Subsystem for Linux). The repo **must** live
> in the WSL filesystem (e.g. `~/src/ClawScout`), **not** in `/mnt/c/...` -- running
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
3. After install: Docker Desktop --> Settings --> Resources --> WSL Integration
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
2. Ollama runs as a service on `localhost:11434` -- WSL can reach it automatically

Verify from a WSL terminal:

```bash
curl -s http://localhost:11434/api/tags | head -c 100
```

### 4. Install Python 3.14+ and Node.js v24+

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

# Make management script executable
chmod +x scripts/clawscout.sh
```

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
|---------|----------|-------------|
| `make up` | `./scripts/clawscout.sh start` | Start everything |
| `make down` | `./scripts/clawscout.sh stop` | Stop everything (preserves data) |
| `make restart` | `./scripts/clawscout.sh restart` | Stop + start |
| `make status` | `./scripts/clawscout.sh status` | Show status of each service |
| `make logs` | `./scripts/clawscout.sh logs` | Live logs |
| `make preflight` | `./scripts/clawscout.sh preflight` | Verify configuration |
| `make seed` | `./scripts/clawscout.sh seed` | Load sample data |
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
|---------|-----|
| Dashboard | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Detailed Health | http://localhost:8000/health/detailed |
| Flower (optional) | http://localhost:5555 |

### Manual Mode (4 terminals)

If you prefer individual control over each process:

```bash
# Terminal 1 -- Infrastructure
docker compose up postgres redis

# Terminal 2 -- API
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 -- Worker
source .venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info

# Terminal 4 -- Dashboard
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

## What Is Automatic vs Manual

In ClawScout v1, **almost everything is manual**. There are no scheduled tasks, no auto-crawl, no Celery Beat. Everything runs when you trigger it.

| Component | Automatic? | How to control |
|-----------|-----------|----------------|
| Crawlers | No -- run manually | Nothing to turn off |
| Enrichment / Scoring / Drafts | No -- triggered via API | Nothing to turn off |
| Reviewer (27b model) | No -- you request it | Nothing to turn off |
| Reply assistant | Toggle in Settings | `reply_assistant_enabled` |
| Auto-classify inbound | Toggle in Settings | `auto_classify_inbound` |
| Automatic reviewer | Toggle in Settings | `reviewer_enabled` |
| Mail inbound sync | Toggle in Settings | `mail_inbound_sync_enabled` |
| WhatsApp alerts | Toggle in Settings | `whatsapp_alerts_enabled` |

Ollama models (4b, 9b, 27b) only consume VRAM when in use. Ollama automatically unloads them from memory after a few minutes of inactivity.

### Disabling AI Features Without Stopping the System

From the dashboard under **Settings > Rules**, you can disable:
- **Reply assistant** -- auto-generates responses to inbound emails
- **Reviewer** -- automatically reviews drafts and messages
- **Auto-classify inbound** -- classifies inbound emails with AI

All these toggles default to `false`, so automatic AI features don't run unless you explicitly enable them.

---

## LLM Configuration

The system uses Ollama with qwen3.5 models assigned by role:

| Role | Default Model | Environment Variable |
|------|--------------|---------------------|
| Leader | `qwen3.5:4b` | `OLLAMA_LEADER_MODEL` |
| Executor | `qwen3.5:9b` | `OLLAMA_EXECUTOR_MODEL` |
| Reviewer | `qwen3.5:27b` | `OLLAMA_REVIEWER_MODEL` |

```bash
# Download required models
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
```

The supported model catalog is configured via `OLLAMA_SUPPORTED_MODELS` in `.env`.
The legacy `OLLAMA_MODEL` variable still works as a fallback for the executor role.

---

## Project Map

```
ClawScout/
|
|-- app/                             # Python backend (FastAPI)
|   |-- main.py                      #   Entrypoint: app factory, middleware, health check
|   |-- api/
|   |   |-- router.py                #   Registers all /api/v1/* routes
|   |   |-- auth.py                  #   API key middleware (X-API-Key)
|   |   |-- deps.py                  #   FastAPI dependency injection (DB session)
|   |   +-- v1/                      #   20 endpoint modules:
|   |       |-- leads.py             #     Lead CRUD
|   |       |-- enrichment.py        #     Data enrichment (sync/async)
|   |       |-- scoring.py           #     Rule-based scoring
|   |       |-- outreach.py          #     Outreach draft management
|   |       |-- pipelines.py         #     Full pipeline orchestration
|   |       |-- settings.py          #     System configuration (22KB, 12 tabs)
|   |       |-- mail.py              #     Inbound/outbound email
|   |       |-- dashboard.py         #     Analytics & metrics
|   |       |-- tasks.py             #     Async task status
|   |       |-- crawl.py             #     Google Maps crawling
|   |       |-- replies.py           #     Email reply management
|   |       |-- reviews.py           #     Manual review workflows
|   |       |-- notifications.py     #     Real-time notifications
|   |       |-- whatsapp.py          #     WhatsApp integration
|   |       |-- telegram.py          #     Telegram bot
|   |       |-- territories.py       #     Geographic regions
|   |       |-- leader.py            #     Leader analysis
|   |       |-- performance.py       #     Performance metrics
|   |       +-- suppression.py       #     Email suppression list
|   |-- core/
|   |   |-- config.py                #   Pydantic settings (all env vars)
|   |   |-- crypto.py                #   Encryption for credentials
|   |   +-- logging.py               #   structlog JSON logging
|   |-- db/
|   |   |-- base.py                  #   SQLAlchemy DeclarativeBase
|   |   +-- session.py               #   Engine, SessionLocal, get_db()
|   |-- models/                      #   19 SQLAlchemy ORM models
|   |   |-- lead.py                  #     Lead, LeadStatus, LeadQuality
|   |   |-- lead_signal.py           #     LeadSignal (11 signal types)
|   |   |-- outreach.py              #     OutreachDraft, OutreachLog, OutreachDelivery
|   |   |-- settings.py              #     OperationalSettings (feature toggles)
|   |   |-- mail.py                  #     MailCredentials, EmailThread, InboundMessage
|   |   |-- task_tracking.py         #     TaskRun, PipelineRun
|   |   |-- notification.py          #     Notification
|   |   |-- territory.py             #     Territory
|   |   +-- ...                      #     WhatsApp/Telegram credentials & audit logs
|   |-- schemas/                     #   20 Pydantic request/response schemas
|   |-- services/                    #   36 service modules (business logic)
|   |   |-- enrichment_service.py    #     Website crawl + signal detection
|   |   |-- leader_service.py        #     Lead analysis orchestration
|   |   |-- outreach_service.py      #     Draft generation + sending
|   |   |-- dashboard_service.py     #     Analytics aggregation
|   |   |-- inbound_mail_service.py  #     IMAP sync + classification
|   |   |-- operational_settings_service.py  # Feature toggle cache
|   |   +-- ...                      #     Mail, WhatsApp, Telegram, replies, notifications
|   |-- workers/
|   |   |-- celery_app.py            #   Celery config, queue routing, beat schedule
|   |   |-- tasks.py                 #   All async tasks (enrich, score, draft, review, crawl)
|   |   +-- janitor.py               #   Stale task cleanup
|   |-- llm/
|   |   |-- client.py                #   Ollama HTTP client (all LLM calls)
|   |   |-- prompts.py               #   System + data prompt templates
|   |   |-- roles.py                 #   LLMRole enum (LEADER, EXECUTOR, REVIEWER)
|   |   |-- catalog.py               #   Model catalog + role defaults
|   |   +-- resolver.py              #   Role -> model resolution
|   |-- mail/
|   |   |-- smtp_provider.py         #   SMTP sending (TLS/SSL)
|   |   |-- imap_provider.py         #   IMAP sync (UID-based)
|   |   +-- provider.py              #   Abstract base class
|   |-- scoring/
|   |   +-- rules.py                 #   Rule-based scoring (0-100 points)
|   |-- outreach/
|   |   +-- generator.py             #   LLM-powered draft generation
|   |-- crawlers/
|   |   |-- base_crawler.py          #   ABC with rate limiting
|   |   +-- google_maps_crawler.py   #   Google Maps API integration
|   +-- data/
|       +-- cities_ar.py             #   Argentine city list for validation
|
|-- dashboard/                       # Next.js 16 frontend (App Router)
|   |-- app/                         #   Routes / pages
|   |   |-- layout.tsx               #     Root layout (fonts, theme, sidebar)
|   |   |-- page.tsx                 #     / -- Overview dashboard
|   |   |-- globals.css              #     Tailwind v4 theme (oklch colors)
|   |   |-- leads/page.tsx           #     /leads -- Lead table
|   |   |-- leads/[id]/page.tsx      #     /leads/:id -- Lead detail
|   |   |-- outreach/page.tsx        #     /outreach -- Draft management
|   |   |-- responses/page.tsx       #     /responses -- Inbound replies
|   |   |-- performance/page.tsx     #     /performance -- Metrics
|   |   |-- suppression/page.tsx     #     /suppression -- Suppression list
|   |   |-- activity/page.tsx        #     /activity -- System log
|   |   |-- map/page.tsx             #     /map -- Interactive lead map
|   |   |-- notifications/page.tsx   #     /notifications -- Alerts
|   |   |-- security/page.tsx        #     /security -- Security config
|   |   +-- settings/page.tsx        #     /settings -- 12-tab configuration
|   |-- components/
|   |   |-- layout/                  #     Sidebar, ActivityPulse, PageHeader, ThemeToggle
|   |   |-- dashboard/               #     ControlCenter, StatsGrid, PipelineFunnel, charts
|   |   |-- shared/                  #     StatCard, StatusBadge, Skeleton, EmptyState, ReplyDraftPanel
|   |   |-- leads/                   #     LeadsTable
|   |   |-- map/                     #     LeadMap, TerritoryPanel, CityMarker, Heatmap
|   |   |-- settings/               #     16 settings section components
|   |   |-- ui/                      #     shadcn/ui (base-ui): button, dialog, dropdown, input, table, tabs, tooltip
|   |   +-- providers/               #     ThemeProvider, ThemedToaster
|   |-- lib/
|   |   |-- api/client.ts            #     Centralized API client (all backend calls)
|   |   |-- constants.ts             #     Status/quality/signal configs, colors
|   |   |-- formatters.ts            #     Date/number formatting (es-AR locale)
|   |   |-- utils.ts                 #     cn() class merging
|   |   +-- hooks/use-page-data.ts   #     Async data loading hook
|   |-- data/
|   |   +-- cities-ar.ts             #     Argentine city coordinates (map fallback)
|   +-- types/
|       +-- index.ts                 #     All TypeScript type definitions (800 lines)
|
|-- alembic/                         # Database migrations (27 versions)
|   |-- env.py                       #   Migration environment config
|   +-- versions/                    #   Sequential schema evolution
|
|-- scripts/                         # Operations & CLI tools
|   |-- clawscout.sh                 #   Main mgmt script (start/stop/status/logs/seed/nuke)
|   |-- dev-up.sh                    #   API + Dashboard only (no Docker)
|   |-- dev-down.sh                  #   Stop dev mode
|   |-- dev-status.sh                #   Dev mode status
|   |-- clawscoutctl.py              #   Data + mutating CLI (leads, drafts, tasks, pipelines)
|   |-- opsctl.py                    #   Operational briefs + leader model integration
|   |-- browserctl.py                #   Website inspection via Playwright
|   |-- mailctl.py                   #   Mail operations CLI
|   |-- preflight.py                 #   Pre-launch validation checks
|   |-- seed.py                      #   Sample data loader
|   |-- ensure-ollama-bridge.sh      #   Restore WSL <-> Windows Ollama connection
|   |-- start-local-stack.sh         #   Guided setup with tmux
|
|-- skills/                          # Hermes agent skills (7 modules)
|   |-- clawscout-data/              #   Read-only grounded data queries
|   |-- clawscout-actions/           #   Mutating operations (drafts, pipeline, reviews)
|   |-- clawscout-briefs/            #   Operational summaries with leader model
|   |-- clawscout-browser/           #   Website inspection via Playwright
|   |-- clawscout-mail/              #   Mail operations
|   |-- clawscout-notifications/     #   Notification management
|   +-- clawscout-whatsapp/          #   WhatsApp integration
|
|-- infra/
|   +-- docker/Dockerfile            # Python backend container image
|
|-- tests/                           # Backend tests (pytest + SQLite)
|   |-- conftest.py                  #   Fixtures, TestClient, session override
|   +-- test_*.py                    #   22 test modules
|
|-- docs/                            # Internal documentation
|   |-- linux-first.md               #   Architecture decisions & validated workflow
|   |-- SECURITY_AUDIT_PENDING.md    #   Security findings tracker
|   +-- superpowers/plans/           #   Implementation plans
|
|-- AGENTS.md                        # Agent framework documentation
|-- SOUL.md                          # Hermes agent core principles
|-- IDENTITY.md                      # Hermes agent identity (template)
|-- HEARTBEAT.md                     # Periodic tasks configuration
|-- TOOLS.md                         # Environment notes
|-- USER.md                          # User context
|-- AUDIT.md                         # Internal audit history
|-- docker-compose.yml               # Service orchestration (6 services)
|-- pyproject.toml                   # Python project config + dependencies
|-- Makefile                         # Make targets (up/down/restart/status/logs)
+-- .env.example                     # Environment variable template (99 vars)
```

### Where to Find Things

| I want to... | Look here |
|--------------|-----------|
| Add a new API endpoint | `app/api/v1/` + register in `app/api/router.py` |
| Add business logic | `app/services/` (stateless functions) |
| Add a new model | `app/models/` + import in `app/models/__init__.py` + alembic migration |
| Change LLM prompts | `app/llm/prompts.py` |
| Add a dashboard page | `dashboard/app/<route>/page.tsx` |
| Add a reusable component | `dashboard/components/shared/` |
| Add a settings tab | `dashboard/components/settings/` + update `types.ts` |
| Call the backend from frontend | `dashboard/lib/api/client.ts` |
| Add an async task | `app/workers/tasks.py` + register queue in `celery_app.py` |
| Add a database migration | `alembic revision --autogenerate -m "description"` |
| Add a Hermes agent skill | `skills/<skill-name>/SKILL.md` |
| Run pre-launch checks | `python scripts/preflight.py` |

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| Overview | `/` | General metrics, visual pipeline, time-series charts |
| Leads | `/leads` | Paginated table with filters, search, and actions |
| Lead Detail | `/leads/[id]` | Detected signals, score, drafts, timeline |
| Outreach | `/outreach` | Draft management: pending, approved, sent |
| Performance | `/performance` | Metrics by industry, city, and source |
| Suppression | `/suppression` | Global suppression list |
| Responses | `/responses` | Inbound replies classified by LLM |
| Activity | `/activity` | System activity log |
| Notifications | `/notifications` | Notifications and alerts |
| Security | `/security` | Security configuration |
| Settings | `/settings` | General system settings |

## API Endpoints

Interactive Swagger docs at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/leads` | Create a lead |
| GET | `/api/v1/leads` | List leads (paginated, filterable) |
| GET | `/api/v1/leads/{id}` | Get lead with signals |
| POST | `/api/v1/enrichment/{id}` | Enrich a lead (sync) |
| POST | `/api/v1/enrichment/{id}/async` | Enrich a lead (async) |
| POST | `/api/v1/scoring/{id}` | Score a lead |
| POST | `/api/v1/scoring/{id}/analyze` | LLM analysis (async) |
| POST | `/api/v1/scoring/{id}/pipeline` | Full pipeline (async) |
| POST | `/api/v1/outreach/{id}/draft` | Generate outreach draft |
| GET | `/api/v1/outreach/drafts` | List drafts |
| POST | `/api/v1/outreach/drafts/{id}/review` | Approve/reject draft |
| POST | `/api/v1/suppression` | Add to suppression list |
| GET | `/api/v1/suppression` | List suppression entries |
| DELETE | `/api/v1/suppression/{id}` | Remove from suppression list |

## Prospecting Pipeline

```
1. Ingest lead (manual or via crawler)
2. Enrich: analyze website, detect signals
3. Score: rule-based scoring from signals
4. LLM Analysis: summarize, evaluate quality, suggest angle
5. Generate outreach draft
6. Human review: approve / reject
7. Send (v2)
```

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
