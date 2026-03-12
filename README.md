# ClawScout v1

Private lead prospecting system for web development services. Detects businesses that need web development/redesign, enriches leads, scores them, generates outreach drafts, and supports human-in-the-loop review.

## Architecture

```
app/
├── api/v1/        # FastAPI endpoints
├── core/          # Config, logging
├── db/            # Database session, base model
├── models/        # SQLAlchemy models
├── schemas/       # Pydantic request/response schemas
├── services/      # Business logic layer
├── workers/       # Celery tasks
├── llm/           # Ollama/Qwen integration
├── scoring/       # Rule-based scoring engine
├── outreach/      # Email draft generation
└── crawlers/      # Lead discovery crawlers
```

**Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL, Redis, Celery, Ollama (default `qwen3.5:9b`), httpx, BeautifulSoup4, structlog.

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Ollama (for local LLM)

## Quick Start

### Windows (PowerShell)

```powershell
.\bootstrap.ps1
```

### Linux / WSL

```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

### Manual Setup

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/WSL
# .\.venv\Scripts\Activate.ps1  # Windows PowerShell

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Copy and edit environment config
cp .env.example .env
# Edit .env with your values

# 4. Start infrastructure
docker compose up -d postgres redis

# 5. Run database migrations
alembic upgrade head

# 6. Pull LLM model
ollama pull qwen3.5:9b

# 7. Seed sample data (optional)
python scripts/seed.py
```

## LLM Defaults

- Active default model: `qwen3.5:9b` via `OLLAMA_MODEL`
- Prepared catalog for future switching: `qwen3.5:4b`, `qwen3.5:9b`, `qwen3.5:27b` via `OLLAMA_SUPPORTED_MODELS`
- The app still uses a single active model today; role-specific model routing is intentionally deferred

## Running

```bash
# API server (with auto-reload)
uvicorn app.main:app --reload

# Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Celery Flower (monitoring dashboard)
celery -A app.workers.celery_app flower --port=5555

# Or run everything via Docker Compose
docker compose up -d
```

## API Endpoints

Once running, visit http://localhost:8000/docs for interactive Swagger docs.

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

## Pipeline Flow

```
1. Ingest lead (manual or crawler)
2. Enrich: analyze website, detect signals
3. Score: rule-based scoring from signals
4. LLM Analysis: summarize, evaluate quality, suggest angle
5. Generate outreach draft
6. Human review: approve / reject
7. (v2) Send email
```

## Tests

```bash
pytest -v
```

## Key Design Decisions

- **Celery over RQ**: Native retry+backoff, task routing (separate queues for crawling/LLM/enrichment), rate limiting per task, Flower monitoring.
- **Sync SQLAlchemy for v1**: Simpler, FastAPI supports it fine. Async migration path is straightforward with SQLAlchemy 2.x.
- **structlog**: Structured JSON logs for auditing and debugging.
- **Dedup via hash**: SHA-256 of normalized (business_name + city + domain). Prevents duplicate leads at insert time.
- **Suppression list enforced globally**: Checked at lead creation, before outreach generation, and on bulk operations.
- **LLM output treated as untrusted**: JSON extraction with fallback, all outputs sanitized before storage.
- **No auto-send in v1**: All outreach requires human approval.

## What's Not in v1 (Roadmap)

- Frontend panel (admin dashboard)
- Email sending integration (SMTP/Resend/etc.)
- Playwright-based deep crawling
- Advanced SEO analysis
- Multi-model LLM support
- Webhook integrations
- Analytics and reporting
- Bulk operations UI
