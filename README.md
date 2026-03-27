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
| OpenClaw | Separate process | Not managed by make up/down |

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

## Project Structure

```
ClawScout/
|-- app/                      # Python backend
|   |-- api/v1/               # FastAPI endpoints
|   |-- core/                 # Config (pydantic-settings), logging (structlog)
|   |-- db/                   # Session factory, Base model
|   |-- models/               # SQLAlchemy models
|   |-- schemas/              # Pydantic request/response schemas
|   |-- services/             # Business logic layer
|   |-- workers/              # Celery app + tasks
|   |-- llm/                  # Ollama client, catalog, roles, prompts
|   |-- mail/                 # Email send/receive
|   |-- scoring/              # Rule-based scoring engine
|   |-- outreach/             # LLM-powered draft generation
|   |-- crawlers/             # BaseCrawler ABC + implementations
|-- dashboard/                # Next.js 16 frontend
|   |-- app/                  # App Router -- pages
|   |-- components/           # UI, shared, charts, layout
|   |-- lib/                  # API client, hooks, constants
|   |-- data/                 # Mock data for development
|   |-- types/                # TypeScript definitions
|-- alembic/                  # Database migrations
|-- infra/                    # Dockerfiles, infra config
|-- scripts/                  # Utility scripts
|-- tests/                    # Backend tests
|-- docker-compose.yml        # Service orchestration
|-- pyproject.toml            # Python project config
|-- .env.example              # Environment variable template
```

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
