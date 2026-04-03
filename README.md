# ClawScout

ClawScout is a modular-monolith lead prospecting platform for web development services.
It crawls businesses, enriches and scores leads, runs AI-assisted research and outreach flows,
and exposes an operational dashboard for human-in-the-loop execution.

## Start Here

- Human operators and developers: start with this file, then see [docs/README.md](docs/README.md).
- AI coding agents: start with [AGENTS.md](AGENTS.md).
- Frontend-only work: see [dashboard/README.md](dashboard/README.md) after this file.

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy 2.x, Celery, structlog |
| Database | PostgreSQL 16, Redis 7 |
| AI | Ollama with local Qwen models |
| Frontend | Next.js 16 App Router, TypeScript, Tailwind CSS v4 |
| Infra | Docker Compose, Alembic |

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

## Repo Map

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI backend, workers, services, models, LLM layer |
| `dashboard/` | Next.js operational frontend |
| `docs/` | Canonical architecture, plans, operations, product, archive |
| `scripts/` | CLI and local operations helpers |
| `tests/` | Backend test suite |
| `alembic/` | Database migrations |

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
