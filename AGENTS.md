# Scouter AI Entry

> **30-second quickstart:** Scouter is a lead prospecting platform (Python/FastAPI + Next.js). 4 AI roles: Mote (agent, 8b), Scout (research agent, 9b), Executor (generator, 9b), Reviewer (quality gate, 27b). Tests: `pytest`. Types: `cd dashboard && npx tsc --noEmit`. Start here, then [docs/README.md](docs/README.md).

This is the canonical entrypoint for AI coding assistants working in Scouter.

Use this file to orient quickly, then follow the task-specific reading path below.
Do not treat archived reports or runtime personality files as the default source of truth.

## What Scouter Is

Scouter is a modular-monolith lead prospecting platform with an AI Agent OS.
The backend handles ingestion, enrichment, scoring, AI-assisted research, outreach, and async workflows.
The frontend is an operational Next.js dashboard.
The Agent OS runs 4 AI roles through a pipeline with accumulated context, structured feedback, and outcome tracking.

## Read Order

### Always first

1. This file.
2. [docs/README.md](docs/README.md).

### Then choose by task

| Task | Read next |
| --- | --- |
| Architecture review or structural refactor | [docs/architecture/audit.md](docs/architecture/audit.md) -> [docs/architecture/target.md](docs/architecture/target.md) -> [docs/plans/refactor-roadmap.md](docs/plans/refactor-roadmap.md) |
| Backend feature or bugfix | `app/api/`, `app/services/`, `app/workflows/`, `app/workers/`, relevant tests |
| Frontend feature or bugfix | [dashboard/README.md](dashboard/README.md), then `dashboard/app/`, `dashboard/components/`, `dashboard/lib/api/client.ts`, `dashboard/types/index.ts` |
| Async workflow work | `app/workflows/`, `app/workers/tasks.py`, `app/services/operational_task_service.py`, `app/services/task_tracking_service.py` |
| AI / agent work | `app/llm/`, `app/agent/`, and only then [SOUL.md](SOUL.md) / [IDENTITY.md](IDENTITY.md) if persona or prompt wiring is relevant |
| Agent OS understanding | [docs/agents/hierarchy.md](docs/agents/hierarchy.md) -> [docs/agents/protocols.md](docs/agents/protocols.md) -> [docs/agents/identities.md](docs/agents/identities.md) |
| Skills / model routing | [skills/MODEL_ROUTING.md](skills/MODEL_ROUTING.md), then `skills/scouter-*/SKILL.md` for domain-specific skills |
| Local operations / environment issues | [README.md](README.md) -> [docs/operations/local-dev-wsl.md](docs/operations/local-dev-wsl.md) |
| Product context | [docs/product/proposal.md](docs/product/proposal.md) |
| Historical archaeology | `docs/archive/` only after reading the canonical docs above |

## Repo Map

| Path | Why it matters |
| --- | --- |
| `app/api/` | HTTP entrypoints and request-facing contracts |
| `app/workflows/` | Explicit workflow orchestration seams |
| `app/workers/` | Celery task wrappers and async execution substrate |
| `app/services/` | Business logic and integration-heavy services |
| `app/models/` | SQLAlchemy ORM models |
| `app/llm/` | Model routing, prompts, invocation logic |
| `app/agent/` | Mote agent loop, prompts, channel routing, tools |
| `dashboard/` | Next.js dashboard |
| `tests/` | Regression and behavior coverage |
| `docs/` | Canonical docs, plans, operations, and archive |

## Editing Conventions

- Keep changes incremental. This repo is being hardened by seam, not rewritten by big bang.
- Prefer canonical docs over archived reports when they disagree.
- Do not move [SOUL.md](SOUL.md) or [IDENTITY.md](IDENTITY.md) unless you have a strong tooling reason.
- Treat `docs/archive/` as historical context, not as instruction priority.
- Update `docs/README.md` when you add or rename canonical documentation.

## Validation Expectations

- Backend deltas: targeted `pytest` and `ruff` on the touched area.
- Frontend deltas: targeted type-check and any relevant UI lint/checks.
- Docs-only deltas: verify internal references and stale path references.

## Key Files

| File | Purpose |
| --- | --- |
| [README.md](README.md) | Human entrypoint and quickstart |
| [docs/README.md](docs/README.md) | Documentation index and hierarchy |
| [docs/architecture/audit.md](docs/architecture/audit.md) | Current-state architecture assessment |
| [docs/architecture/target.md](docs/architecture/target.md) | Target architecture direction |
| [docs/plans/refactor-roadmap.md](docs/plans/refactor-roadmap.md) | Incremental refactor sequence |
| [docs/agents/context.md](docs/agents/context.md) | Secondary operator and agent context |
| [SOUL.md](SOUL.md) | Runtime persona asset for Mote |
| [IDENTITY.md](IDENTITY.md) | Runtime identity asset for Mote |

## Runtime Assets vs Documentation

- [SOUL.md](SOUL.md) and [IDENTITY.md](IDENTITY.md) are runtime inputs consumed by `app/agent/prompts.py`.
- They are not the main onboarding path for either humans or coding agents.
