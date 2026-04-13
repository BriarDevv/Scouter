> **ARCHIVED:** This document has been superseded. See [architecture/audit.md](../../architecture/audit.md) for the current version.

# Scouter Repository Architecture Deep Audit

**Date:** 2026-04-06
**Auditor:** Claude Opus 4.6 acting as Principal Engineer + Repo Architect + DX Auditor + AI Navigation Specialist
**Scope:** Full repository — every folder, every file, every boundary
**Repo state:** main branch, 227 Python files, 128 TS/TSX files, 47 test files, 43 migrations, 47 docs

---

## Executive Summary

Scouter is a well-structured modular monolith that has undergone significant hardening since its last architecture audit (2026-04-04, score 6.2/10). The backend shows strong domain-driven sub-packaging in `services/`, extracted workflows, thin worker dispatchers, and a clean LLM abstraction layer. The frontend has good component-level domain organization but is architecturally stalled as a pure client-side SPA despite using Next.js App Router.

The repo is **significantly above average** for a single-maintainer product codebase. It has real documentation, real tests, real CI discipline, and real AI-agent navigability. But it is not a 10/10 — three structural forces prevent that:

1. **Services layer coupling** — 40+ cross-service imports and 98 `db.commit()` calls inside services make composition fragile.
2. **Frontend as pure SPA** — 16/16 pages are `"use client"`, zero server components, monolithic type/client files.
3. **Transaction boundary ownership** — no single layer owns the unit of work; every service commits independently.

**Overall Architecture Score: 7.5 / 10**

---

## Evidence Snapshot

| Metric | Count |
| --- | ---: |
| Python source files (`app/`) | 227 |
| TypeScript/TSX files (`dashboard/`) | 128 |
| Backend LOC (`app/`) | 29,733 |
| Frontend LOC (`dashboard/`) | 20,777 |
| Test files (backend) | 47 |
| Test files (frontend) | 8 + 3 e2e |
| Alembic migrations | 43 |
| API routers | 24 |
| Celery task modules | 9 |
| Service sub-packages | 10 |
| Agent tools | 15 |
| LLM invocation types | 6 |
| Documentation files | 47 |
| Claude Code commands | 10 |
| Agent skills | 8 |
| `"use client"` directives | 98 |
| `db.commit()` in services | 98 |
| `db.commit()` in workers | 7 |
| `db.commit()` in API | 1 |
| Broad `except Exception` catches | 131 |
| Bare `except:` catches | 0 |
| Cross-service imports | 40+ |
| Root-level files | 16 |

---

## Folder-by-Folder Audit

### 1. `app/api/` — HTTP Router Layer (3,611 LOC)

**Purpose:** HTTP entrypoints, request validation, response mapping.

| Sub-path | Files | LOC | Purpose |
| --- | ---: | ---: | --- |
| `v1/` | 24 routers | ~3,200 | Domain-specific REST endpoints |
| `v1/settings/` | 4 files | ~400 | Settings split: credentials, messaging, operational, readonly |
| `auth.py` | 1 | ~60 | API key middleware |
| `request_context.py` | 1 | ~80 | Request/correlation ID middleware |
| `router.py` | 1 | ~54 | Central router registration |

**Strengths:**
- Clean flat structure — one router file per domain.
- Settings wisely split into 4 sub-files instead of one god router.
- Only 1 `db.commit()` found in the entire API layer (`pipelines.py:144`).
- `request_context.py` adds correlation IDs — good observability foundation.
- Central `router.py` is a clean manifest of all 24 routers.

**Issues:**
- **`ai_office.py` (423 LOC) is a god router** — contains 15+ raw SQLAlchemy queries inline, imports 8 model classes, builds complex aggregation dicts. Defines Pydantic models inline (`TestWhatsAppBody`, `CloserReplyBody`) instead of in `schemas/`. All this logic belongs in a service.
- `pipelines.py:102-153` — `resume_pipeline_run` endpoint contains a hardcoded `step_chain` dict and directly imports task modules to dispatch. This is business logic that belongs in a workflow.
- `pipelines.py:144` has a direct `db.commit()` — routers should not own persistence.
- Some routers import directly from `app.workers` to dispatch Celery tasks (13 imports) — acceptable but couples HTTP layer to task infrastructure.
- `performance.py` has lazy imports of `LLMInvocation` model and raw queries inside endpoint bodies.

**Scores:** Purpose 9 | Naming 9 | Cohesion 7 | Scalability 9

---

### 2. `app/services/` — Business Logic Layer (10,008 LOC)

This is the largest and most complex area of the codebase.

| Sub-package | Files | Approx LOC | Purpose |
| --- | ---: | ---: | --- |
| `comms/` | 6 | ~1,100 | WhatsApp, Telegram, Kapso integrations |
| `dashboard_svc/` | 3 | ~1,000 | Dashboard aggregations, health, leader |
| `inbox/` | 5 | ~1,300 | Inbound mail, reply classification/drafting/sending |
| `leads/` | 3 | ~700 | Lead CRUD, enrichment, scoring |
| `notifications/` | 2 | ~600 | Notification creation + channel dispatch |
| `outreach/` | 6 | ~1,200 | Draft generation, mail sending, auto-send, closer |
| `pipeline/` | 5 | ~1,800 | Task tracking, batch reviews, operational tasks, outcomes |
| `research/` | 4 | ~800 | Research, briefs, storage, export |
| `settings/` | 3 | ~600 | Operational settings, setup status |
| Root-level | 5 | ~900 | review, territory, suppression, setup, instagram |

**Strengths:**
- 10 sub-packages with clear domain alignment — this is above-average structure.
- Sub-packages group related files: `inbox/` has classification, drafting, review, sending.
- Most services follow the pattern: import models/schemas, operate on DB session, return results.

**Issues:**
- **Cross-service coupling is the #1 structural problem.** 40+ cross-service imports detected:
  - `notification_emitter` is called from `outreach`, `inbox`, `research`, `leads`.
  - `operational_settings_service` is imported by nearly everyone (batch_review, inbox, notifications, outreach, research).
  - `notification_service` calls `whatsapp_service` and `telegram_service` inline.
  - `settings_service` imports from `inbox` and `outreach`.
- **98 `db.commit()` calls inside services** — transaction boundaries are not owned by a coordinator.
- **Deferred imports used to avoid circular dependencies** — a code smell indicating coupling.
- `dashboard_svc` naming inconsistent with other sub-packages (uses `_svc` suffix, others don't).
- `instagram_scraper.py` sits at the root instead of in a `crawlers/` or `comms/` sub-package.
- `setup_service.py` (426 LOC) at root — could be in `settings/`.

**Scores:** Purpose 7 | Naming 7 | Cohesion 6 | Scalability 6

---

### 3. `app/models/` — ORM Layer (2,215 LOC)

| Pattern | Evidence |
| --- | --- |
| Files | 29 model files (one per domain entity) |
| Naming | `snake_case.py` matching domain entity names |
| Inheritance | All inherit from `Base` in `app/db/base.py` |

**Strengths:**
- One file per model — clean, discoverable.
- Consistent naming: `lead.py`, `outreach.py`, `notification.py`.
- Good use of SQLAlchemy 2.x `Mapped[]` type annotations.

**Issues:**
- 1 layer violation: `models/llm_invocation.py` imports `from app.llm.types import LLMInvocationStatus` — models should not depend on LLM layer.
- `LeadStatus` enum still overloaded (processing stages + CRM lifecycle in one enum) — identified in prior audit, not yet split.
- `settings.py` is a god model (`OperationalSettings` singleton absorbing too many concerns).

**Scores:** Purpose 9 | Naming 9 | Cohesion 8 | Scalability 8

---

### 4. `app/llm/` — LLM Abstraction Layer (3,338 LOC)

| File | LOC | Purpose |
| --- | ---: | --- |
| `prompts.py` | 714 | All prompt templates |
| `client.py` | 599 | Ollama client with parse/retry |
| `invocations/` | 6 files | Domain-specific invocation wrappers |
| `catalog.py` | ~100 | Model catalog |
| `contracts.py` | ~150 | Pydantic response schemas |
| `types.py` | ~80 | Shared types/enums |
| `roles.py` | ~50 | LLM role definitions |
| `resolver.py` | ~60 | Model resolution by role |
| `sanitizer.py` | ~80 | Input/output sanitization |
| `prompt_registry.py` | ~100 | Prompt registration system |
| `invocation_metadata.py` | ~80 | Invocation tracking |

**Strengths:**
- Clear separation: `client.py` handles transport, `invocations/` handles domain-specific call shapes.
- `contracts.py` with Pydantic schemas for structured LLM outputs.
- `roles.py` + `resolver.py` for role-based model routing.
- `sanitizer.py` for prompt injection defense.
- `invocations/` sub-package with per-domain files (lead, outreach, reply, research, batch_review, support).
- Zero imports from `app.services` — clean boundary!

**Issues:**
- `prompts.py` at 714 LOC is the largest file — could be split per domain.
- `client.py` at 599 LOC still relies on regex JSON extraction for some paths.
- `invocation_metadata.py` exists but prior audit noted no formal invocation table with latency/prompt version yet.

**Scores:** Purpose 9 | Naming 9 | Cohesion 9 | Scalability 8

---

### 5. `app/agent/` — Agent OS Layer (4,126 LOC)

| File/Dir | LOC | Purpose |
| --- | ---: | --- |
| `tools/` | 15 files | One file per tool domain |
| `core.py` | 397 | Agent execution loop |
| `scout_tools.py` | 407 | Scout-specific Playwright tools |
| `scout_prompts.py` | ~120 | Scout prompt builder |
| `prompts.py` | ~200 | Mote prompt builder |
| `streaming_client.py` | ~150 | Ollama streaming adapter |
| `tool_registry.py` | ~100 | Tool registration system |
| `channel_router.py` | ~80 | Multi-channel conversation routing |
| `events.py` | ~60 | Event definitions |
| `hermes_format.py` | ~50 | Hermes-3 format adapter |
| `research_agent.py` | ~80 | Research agent orchestrator |

**Strengths:**
- `tools/` sub-package with 15 domain-specific files — excellent granularity.
- Clean separation: `core.py` (loop), `streaming_client.py` (transport), `tool_registry.py` (discovery).
- Scout tools separated from Mote tools.
- 27 imports from `app.services` (expected — tools are the bridge between agent and business logic).

**Issues:**
- `scout_tools.py` at 407 LOC is large — could be split into navigation/extraction sub-modules.
- `core.py` handles execution + persistence + tool dispatch in one loop — the medium-3 finding from prior audit.

**Scores:** Purpose 9 | Naming 8 | Cohesion 8 | Scalability 8

---

### 6. `app/workers/` — Celery Task Layer (2,401 LOC)

| File | LOC | Purpose |
| --- | ---: | --- |
| `pipeline_tasks.py` | 580 | Pipeline step task definitions |
| `review_tasks.py` | 323 | Review task definitions |
| `research_tasks.py` | 299 | Research task definitions |
| `batch_tasks.py` | ~200 | Batch pipeline task |
| `celery_app.py` | 95 | Celery config + beat schedule |
| `tasks.py` | ~26 | Thin task dispatcher (refactored) |
| `brief_tasks.py` | ~180 | Brief generation tasks |
| `crawl_tasks.py` | ~180 | Territory crawl tasks |
| `weekly_tasks.py` | ~120 | Weekly report task |
| `janitor.py` | ~80 | Stale task sweeper |
| `_helpers.py` | ~50 | Shared helpers |

**Strengths:**
- `tasks.py` refactored to thin 26-LOC dispatcher — massive improvement from prior audit.
- Clear per-domain task files.
- `celery_app.py` with queue routing, LOW_RESOURCE_MODE, beat schedule — well-configured.
- `_helpers.py` for shared patterns.

**Issues:**
- `pipeline_tasks.py` at 580 LOC is still the thickest — contains actual step execution logic, not just dispatch.
- 7 `db.commit()` calls — workers should delegate persistence to services.

**Scores:** Purpose 8 | Naming 8 | Cohesion 7 | Scalability 7

---

### 7. `app/workflows/` — Workflow Orchestration (973 LOC)

| File | LOC | Purpose |
| --- | ---: | --- |
| `lead_pipeline.py` | 216 | Lead analysis/research/draft steps |
| `batch_pipeline.py` | 284 | Batch orchestration |
| `territory_crawl.py` | ~200 | Territory crawl workflow |
| `outreach_draft_generation.py` | ~270 | Draft generation + automation |

**Strengths:**
- Explicit workflow extraction from workers — this layer didn't exist before refactoring.
- `lead_pipeline.py` uses clean dataclass results (`LeadAnalysisStepResult`, `HighValueLaneResult`).
- Batch pipeline delegates to lead pipeline steps — DRY.

**Issues:**
- `batch_pipeline.py` still has `db.commit()` inside (should be coordinator-owned).
- `lead_pipeline.py:152` does `from app.llm.client import review_commercial_brief_structured` — deep import from workflow to LLM internals.

**Scores:** Purpose 9 | Naming 9 | Cohesion 8 | Scalability 8

---

### 8. `app/schemas/` — Pydantic Schemas (1,394 LOC)

**Strengths:**
- One file per domain, mirrors model names.
- Clear request/response schema separation.

**Issues:**
- 11 imports from `app.models` — schemas are tightly coupled to ORM models (importing enums, status types).
- This coupling means schema changes can cascade to model changes and vice versa.

**Scores:** Purpose 8 | Naming 9 | Cohesion 7 | Scalability 7

---

### 9. `app/crawlers/` — Web Crawling (355 LOC)

Two files: `base_crawler.py` + `google_maps_crawler.py`. Clean, focused, no issues.

**Scores:** Purpose 9 | Naming 9 | Cohesion 9 | Scalability 9

---

### 10. `app/mail/` — Mail Providers (408 LOC)

Four files: `provider.py`, `smtp_provider.py`, `imap_provider.py`, `inbound_provider.py`. Clean adapter pattern.

**Scores:** Purpose 9 | Naming 9 | Cohesion 9 | Scalability 9

---

### 11. `app/outreach/` — Outreach Generator (214 LOC)

Single file: `generator.py`. Vestigial package — most outreach logic lives in `services/outreach/`.

**Issue:** This package has minimal reason to exist separately from `services/outreach/`. The generator could live there.

**Scores:** Purpose 5 | Naming 7 | Cohesion 5 | Scalability 5

---

### 12. `app/scoring/` — Scoring Rules (123 LOC)

Single file: `rules.py`. Pure business rules, no dependencies on services or workers.

**Scores:** Purpose 9 | Naming 9 | Cohesion 10 | Scalability 9

---

### 13. `app/core/` — Core Utilities (336 LOC)

Three files: `config.py`, `crypto.py`, `logging.py`. Clean foundation layer.

**Scores:** Purpose 10 | Naming 10 | Cohesion 10 | Scalability 9

---

### 14. `app/db/` — Database Layer (30 LOC)

Two files: `base.py` (declarative base), `session.py` (session factory + `get_db` dependency). Minimal and correct.

**Issue:** `config.py` imports `app.llm.catalog` at module level, creating a `core/` -> `llm/` upward dependency. The LLM package loads whenever config loads. `core/` should have zero upward dependencies.

**Scores:** Purpose 9 | Naming 10 | Cohesion 9 | Scalability 9

---

### 15. `app/data/` — Static Data (97 LOC)

Single file: `cities_ar.py`. Argentine city list for territory crawling.

**Scores:** Purpose 8 | Naming 8 | Cohesion 10 | Scalability 8

---

## Frontend Architecture Audit

### `dashboard/app/` — App Router Pages (5,745 LOC)

| Finding | Evidence |
| --- | --- |
| Total pages | 16 (+ 1 dynamic `[id]`) |
| Client pages | **16/16** — every single page is `"use client"` |
| Server pages | **0/16** |
| Loading states | 4 of 16 pages (`activity`, `leads`, `panel`, `performance`) |
| Error boundaries | 1 global (`app/error.tsx`) — no per-page |
| Largest pages | `responses/page.tsx` (550), `leads/[id]/page.tsx` (550), `outreach/page.tsx` (497), `onboarding/page.tsx` (485) |

**Critical issue:** The App Router is being used as a pure client-side SPA shell. Zero server components for data loading. Every page fetches data client-side via `usePageData` hook. This defeats the primary value proposition of App Router (server-first rendering, streaming, reduced client bundle).

### `dashboard/components/` — Component Library (11,743 LOC)

| Folder | Files | Purpose | Largest File |
| --- | ---: | --- | --- |
| `dashboard/` | 14 | Main dashboard widgets | `control-center.tsx` (434) |
| `settings/` | 14 | Settings form sections | `settings-primitives.tsx` (405) |
| `leads/` | 11 | Lead table + detail panels | `leads-table.tsx` (302) |
| `shared/` | 10 | Reusable primitives | `reply-draft-panel.tsx` (596) |
| `ui/` | 7 | shadcn/ui base components | `dropdown-menu.tsx` (268) |
| `chat/` | 6 | Chat panel + messages | `chat-panel.tsx` (~250) |
| `map/` | 6 | Lead map + markers | `territory-panel.tsx` (401) |
| `layout/` | 6 | Shell, sidebar, header | `sidebar.tsx` (~200) |
| `ai-office/` | 3 | Pipeline runs + reviews | |
| `providers/` | 2 | Theme + toaster | |
| `performance/` | 1 | AI score panel | |
| `charts/` | 1 | Area chart card | |

**Strengths:**
- Domain-organized folders (leads, chat, map, settings, dashboard).
- `shared/` for cross-cutting reusable components.
- `ui/` for shadcn/ui primitives — correct separation.
- File naming is consistently kebab-case.

**Issues:**
- `shared/reply-draft-panel.tsx` at 596 LOC is the largest component — it's a feature component, not a shared primitive. Should live in `leads/` or a new `replies/` folder.
- `shared/notification-list-view.tsx` at 541 LOC — same issue.
- 98 `"use client"` directives means essentially everything is client-rendered.

### `dashboard/lib/` — Utilities (1,491 LOC)

| File | LOC | Issue |
| --- | ---: | --- |
| `api/client.ts` | 884 | God module — all API calls in one file |
| `hooks/use-page-data.ts` | ~60 | Generic fetch hook — no caching, no SWR |
| `hooks/use-chat.ts` | ~100 | Chat-specific hook |
| `hooks/use-chat-panel.tsx` | ~80 | Chat panel context |
| `hooks/use-system-health.ts` | ~50 | Health polling |
| `formatters.ts` | ~100 | Display formatters |
| `constants.ts` | ~30 | URL constants |
| `utils.ts` | ~20 | cn() utility |
| `task-utils.ts` | ~60 | Task status helpers |

**Critical issue:** `api/client.ts` at 884 LOC is a monolithic API client. All 60+ API calls live in one file. Worse, it defines **10 inline interfaces** (`TelegramCredentials`, `BatchPipelineProgress`, `AiHealthData`, `ScoringRecommendation`, `OutcomeAnalysisSummary`, `WeeklyReportData`, `OutboundConversation`, `BatchReviewProposal`, `BatchReviewSummary`, `BatchReviewDetail`) that are then imported from `@/lib/api/client` instead of `@/types` — splitting type authority into two locations.

### `dashboard/types/index.ts` — Type Definitions (982 LOC)

**Critical issue:** Single file containing ALL TypeScript types (40+ interfaces). Hand-maintained, not generated from backend schemas. Combined with the 10 inline types in `api/client.ts`, type authority is split across two files — the primary contract drift risk identified in prior audits.

### Frontend State Management (Newly Identified)

**High-severity pattern:** Pages use extreme `useState` proliferation instead of custom hooks or reducers:
- `app/leads/[id]/page.tsx` — **19 `useState` calls** (lead, drafts, logs, pipelineRuns, inboundMessages, etc.)
- `app/outreach/page.tsx` — **14 `useState` calls**
- `app/responses/page.tsx` — **13 `useState` calls**

The existing `usePageData<T>` hook at `lib/hooks/use-page-data.ts` handles loading/error/data/refresh generically, but most pages manually reimplement this same pattern with raw `useState` + `useEffect` + `try/catch/finally`.

### `dashboard/tests/` — Frontend Tests (528 LOC, 8 files)

Tests exist for: `api-client`, `constants`, `formatters`, `hooks`, `notification-list-view`, `readiness-gate`, `task-utils`. Reasonable but thin coverage for 128 components/files.

### `dashboard/e2e/` — E2E Tests (198 LOC, 3 files)

Onboarding-focused e2e tests with Playwright config. Narrow scope.

---

## Support Structure Audit

### Root Files (16 files)

| File | Justified? | Notes |
| --- | --- | --- |
| `AGENTS.md` | Yes | Canonical AI entrypoint — excellent |
| `CLAUDE.md` | Yes | Claude Code shim to AGENTS.md |
| `CODEX.md` | Marginal | Only needed if using Codex |
| `GEMINI.md` | Marginal | Only needed if using Gemini |
| `IDENTITY.md` | Yes | Runtime asset for Mote agent |
| `SOUL.md` | Yes | Runtime asset for Mote agent |
| `README.md` | Yes | Human entrypoint |
| `LICENSE` | Yes | Standard |
| `Makefile` | Yes | DX entrypoint |
| `pyproject.toml` | Yes | Python config |
| `alembic.ini` | Yes | Migration config |
| `docker-compose.yml` | Yes | Stack definition |
| `.editorconfig` | Yes | Editor consistency |
| `.dockerignore` | Yes | Build optimization |
| `.gitignore` | Yes | Standard |
| `.env.example` | Yes | Config template |

**Issue:** Root has 7 markdown files. `CODEX.md` and `GEMINI.md` add marginal value — they're AI-tool-specific shims that could be consolidated or placed in `.codex/` and `.gemini/` respectively.

### `scripts/` (15 files)

Well-organized: `scouter.sh` as main orchestrator, `dev-up/down/status.sh` for local dev, `scouterctl.py` for CLI operations, `preflight.py` for system checks, `seed.py` for data seeding.

**Issue:** `migrate-legacy-stack.sh` may be dead — legacy migration from what?

### `alembic/versions/` (43 migrations)

Good migration discipline. Naming uses Alembic's hash-prefix convention. One merge migration (`a0d285b111e7_merge_migration_heads.py`) present — normal for a growing codebase.

### `docs/` (47 files)

Excellent documentation structure:
- `docs/README.md` as index with "Start Here By Goal" matrix.
- `architecture/` with audit, target, and 3 ADRs.
- `agents/` with 9 files covering hierarchy, protocols, governance, identities, skills.
- `operations/` with install, local-dev, runbook, security backlog.
- `archive/` properly separated from canonical docs.

**This is the best-documented single-maintainer codebase I've audited.**

### `skills/` (8 files)

`MODEL_ROUTING.md` + 7 domain skills (actions, briefs, browser, data, mail, notifications, whatsapp). Each skill has a `SKILL.md` in its own folder. Clean structure.

### `.claude/commands/` (10 files)

Well-organized Claude Code commands for common operations (agent-os, new-component, new-endpoint, new-page, preflight, stack, test, ux-guidelines, repo audits).

**CRITICAL:** 4 command files contain stale `/home/mateo` paths (7 occurrences) — `preflight.md`, `stack.md`, `test.md`, `agent-os.md`. The current path is `/home/briar/src/Scouter`. These commands **will fail** when invoked. Additionally, `test.md` references "SQLite" when tests actually use PostgreSQL via testcontainers.

### `infra/docker/Dockerfile`

27 lines. Uses `python:3.12-slim`, creates non-root user, correct layer ordering.

**Issue:** `pip install --no-cache-dir .` at line 16 resolves dependencies at build time with no lockfile. Builds are not reproducible.

### `skills/` — Fragile Paths

All 5 domain skill files hardcode `/home/briar/src/Scouter`. If the repo is cloned elsewhere, all skills break.

### State/Runtime Files

All properly `.gitignore`d: `.dev-runtime/`, `.pids/`, `logs/`, `scouter.egg-info/`, `celerybeat-schedule`, `.omc/`. No state leaking into git.

---

## Architectural Best Practices Checklist

| Practice | Status | Evidence |
| --- | --- | --- |
| Clear separation of concerns | Partial | Good folder structure, but services layer coupling undermines it |
| Predictable structure | Strong | Consistent patterns across all backend areas |
| Consistent naming conventions | Strong | snake_case (Python), kebab-case (frontend), one anomaly (`dashboard_svc`) |
| Domain-driven grouping | Strong | 10 service sub-packages aligned to business domains |
| No leaking abstractions | Partial | 1 `db.commit()` in router, 13 worker imports in API, schemas coupled to models |
| No circular dependencies | Strong | Only 1 service-to-worker reverse import, deferred imports used to break cycles |
| Infra separated from business logic | Partial | `mail/`, `crawlers/` clean; but `comms/` mixes infra + business |
| UI not tightly coupled to backend | Weak | Manual type mirrors, manual API client, no contract generation |

---

## AI Navigation Score: 8.5 / 10

### What helps AI navigate this repo:

1. **AGENTS.md** is an exceptional entrypoint — 30-second quickstart, read-order matrix, repo map, editing conventions, validation expectations. This alone puts the repo in the top 5% for AI navigability.
2. **docs/README.md** with goal-based reading paths.
3. **10 Claude Code commands** for common operations.
4. **8 agent skills** with domain-specific context.
5. **3 ADRs** documenting key decisions.
6. **Consistent naming** — an AI can predict file locations from domain concepts.
7. **One model per file** — easy to find entity definitions.
8. **Clear folder purposes** — `workers/` has workers, `services/` has services, `schemas/` has schemas.

### What confuses AI:

1. **Cross-service imports** — an AI following a business flow must traverse 3-5 service files, encountering deferred imports and circular references.
2. **29 duplicate base filenames** across layers (e.g., `lead.py` in models, schemas, api) — AI must pay attention to full paths.
3. **`dashboard_svc` naming** inconsistent with other sub-packages.
4. **`outreach/` package at app level** vs `services/outreach/` — which one does outreach logic live in?
5. **Monolithic `types/index.ts`** — AI must search through 982 LOC to find a type definition.

### Where AI would hallucinate or misinterpret:

- An AI asked to "add a new service" might place it at `services/` root or create a new sub-package — both are valid patterns and there's no documented convention for which to choose.
- An AI modifying outreach logic might look in `app/outreach/` first and miss that the real logic is in `services/outreach/`.
- An AI working on the frontend might assume server components are possible for pages — they're not, because every page is currently `"use client"`.

---

## Human DX Score: 7.5 / 10

### What works well:

1. **Makefile** with `make up`, `make down`, `make test`, `make migrate`, `make dev-up` — instant productivity.
2. **`docker-compose.yml`** with healthchecks, proper service dependencies, Flower UI.
3. **`scripts/preflight.py`** for system readiness checks.
4. **`scripts/seed.py`** for dev data.
5. **`.env.example`** with documented defaults.
6. **47 test files** with real PostgreSQL via testcontainers.
7. **`docs/operations/local-dev-wsl.md`** for WSL setup.
8. **Conventional commits** with documented format.
9. **Ruff + mypy** configured in `pyproject.toml`.

### What hurts DX:

1. **No documented "add a new feature" workflow** — where do I put new code?
2. **Frontend has no component storybook or visual test tooling.**
3. **Only 4/16 pages have loading states** — inconsistent UX during development.
4. **Only 1 global error boundary** — per-page error isolation missing.
5. **No CI pipeline visible in repo** — builds/tests presumably run somewhere but no `.github/workflows/` or equivalent.

---

## Smell Detection

### Confirmed Smells

| Smell | Location | Severity |
| --- | --- | --- |
| **Broken commands** | 4 `.claude/commands/` files with stale `/home/mateo` paths (7 occurrences) | Critical |
| **God router** | `app/api/v1/ai_office.py` (423 LOC, 15+ raw DB queries, 8 model imports) | High |
| **God layer** | `app/services/` (10,008 LOC, 40+ cross-imports) | High |
| **God file** | `dashboard/types/index.ts` (982 LOC) | High |
| **God file** | `dashboard/lib/api/client.ts` (884 LOC, 10 inline types) | High |
| **Transaction boundary fragmentation** | 98 `db.commit()` in services | High |
| **useState proliferation** | `leads/[id]/page.tsx` (19 useState), `outreach/page.tsx` (14), `responses/page.tsx` (13) | High |
| **Split type authority** | 10 interfaces in `api/client.ts` vs 40+ in `types/index.ts` | Medium |
| **Upward dependency** | `app/core/config.py` imports `app.llm.catalog` — core depends on llm | Medium |
| **God service** | `pipeline/task_tracking_service.py` (577 LOC, 4-5 responsibilities) | Medium |
| **Duplicate logic** | `leader_service.py` has `_reply_priority_score()` in Python AND SQL | Medium |
| **Hardcoded step chain** | Pipeline step sequence defined in 3 places (tasks, router, workflow) | Medium |
| **Misplaced component** | `shared/reply-draft-panel.tsx` (596 LOC feature component in shared/) | Medium |
| **Misplaced component** | `shared/notification-list-view.tsx` (541 LOC feature component in shared/) | Medium |
| **Vestigial package** | `app/outreach/` (214 LOC, 1 file) | Medium |
| **Legacy parallel** | `scout_tools.py` alongside `tools/` directory — dual registration approaches | Medium |
| **Naming inconsistency** | `dashboard_svc` vs all other sub-packages | Low |
| **Layer violation** | `models/llm_invocation.py` imports `app.llm.types` | Low |
| **Stale tech reference** | `.claude/commands/test.md` says "SQLite" — tests use PostgreSQL | Low |
| **Missing loading states** | 12/16 pages have no loading.tsx | Low |
| **Missing error boundaries** | No per-page error.tsx | Low |
| **No dependency pinning** | `infra/docker/Dockerfile` — `pip install` without lockfile | Low |
| **Hardcoded skill paths** | 5 skill files hardcode `/home/briar/src/Scouter` | Low |

### Suspected Smells

| Smell | Location | Confidence |
| --- | --- | --- |
| Script overlap | `scripts/start-local-stack.sh` (290 LOC) duplicates `scouter.sh` + `dev-up.sh` | High |
| Over-coupling | `operational_settings_service` as universal import | High |
| Hidden circular deps | Deferred imports in 15+ locations | High |
| Superseded audits | 2-3 audit files in `docs/audits/` superseded by "third pass" audit | Medium |
| Unused module | `app/llm/sanitizer.py` — not imported by `client.py` | Medium |

---

## Structural Consistency Audit

### Naming Consistency

| Area | Convention | Consistent? |
| --- | --- | --- |
| Python files | `snake_case.py` | Yes |
| Python packages | `snake_case/` | Yes (except `dashboard_svc`) |
| Frontend files | `kebab-case.tsx` | Yes |
| Frontend folders | `kebab-case/` | Yes |
| Model files | One per entity | Yes |
| Schema files | One per domain | Yes |
| Router files | One per domain | Yes |
| Worker files | `*_tasks.py` | Yes |
| Tool files | One per domain | Yes |

### Pattern Drift

| Pattern | Area A | Area B | Drift? |
| --- | --- | --- | --- |
| Service sub-packages | `inbox/`, `leads/`, `outreach/` | `dashboard_svc/` | Naming drift |
| Root-level services | `review_service.py`, `territory_service.py` | Sub-packaged services | Structural drift — some at root, some in packages |
| Import style | Module-level imports | Deferred `from X import Y` inside functions | Mixed pattern |
| Error handling | `except Exception` with logging | `except Exception` with pass | Inconsistent (mostly fixed) |
| Logging | `from app.core.logging import get_logger` | `import structlog` | Mostly normalized |

---

## Kill List (Structure Edition)

### Folders to Merge or Dissolve

| Action | Target | Into | Why |
| --- | --- | --- | --- |
| Merge | `app/outreach/` | `app/services/outreach/` | Vestigial 1-file package; generator logic belongs with outreach service |
| Rename | `app/services/dashboard_svc/` | `app/services/dashboard/` | Naming consistency |
| Move | `app/services/instagram_scraper.py` | `app/crawlers/` or `app/services/comms/` | Misplaced at services root |
| Move | `app/services/setup_service.py` | `app/services/settings/` | Logically belongs with settings |
| Move | `dashboard/components/shared/reply-draft-panel.tsx` | `dashboard/components/leads/` or new `replies/` | Feature component, not shared primitive |
| Move | `dashboard/components/shared/notification-list-view.tsx` | `dashboard/components/notifications/` (new) | Feature component, not shared primitive |

### Files to Split

| Action | Target | Into | Why |
| --- | --- | --- | --- |
| Split | `dashboard/types/index.ts` (982 LOC) | Per-domain type files | God file, contract drift risk |
| Split | `dashboard/lib/api/client.ts` (884 LOC) | Per-domain API modules | God file, hard to navigate |
| Split | `app/llm/prompts.py` (714 LOC) | Per-domain prompt files | Largest Python file, growing |

### Files to Fix Immediately

| File | Issue | Action |
| --- | --- | --- |
| `.claude/commands/preflight.md` | Stale `/home/mateo` path | Replace with current path |
| `.claude/commands/stack.md` | Stale `/home/mateo` path (3 occurrences) | Replace with current path |
| `.claude/commands/test.md` | Stale `/home/mateo` path + "SQLite" reference | Fix both |
| `.claude/commands/agent-os.md` | Stale `/home/mateo/Scouter` (wrong structure too) | Fix path |

### Files to Delete (if confirmed dead)

| File | Evidence | Action |
| --- | --- | --- |
| `scripts/migrate-legacy-stack.sh` | Legacy migration — check if still needed | Verify and delete |
| `scripts/start-local-stack.sh` | 290 LOC, 70%+ overlaps `scouter.sh` + `dev-up.sh` | Merge tmux feature or deprecate |

---

## Ideal Structure Proposal

### Backend (incremental, not rewrite)

```
app/
  core/                    # (keep) config, crypto, logging
  db/                      # (keep) base, session
  data/                    # (keep) static data

  models/                  # (keep) one file per entity
  schemas/                 # (keep) one file per domain

  api/                     # (keep) thin routers
    v1/
      settings/            # (keep) split settings

  services/                # Refine boundaries
    comms/                 # (keep)
    dashboard/             # (rename from dashboard_svc)
    inbox/                 # (keep)
    leads/                 # (keep)
    notifications/         # (keep)
    outreach/              # (keep, absorb app/outreach/)
    pipeline/              # (keep)
    research/              # (keep)
    settings/              # (keep, absorb setup_service.py)
    crawlers/              # (NEW — absorb app/crawlers/ + instagram_scraper)

  llm/                     # (keep) — split prompts.py by domain
    invocations/           # (keep)
    prompts/               # (NEW subfolder)

  agent/                   # (keep)
    tools/                 # (keep)

  workers/                 # (keep) — push commit() down to services
  workflows/               # (keep) — push commit() down to services

  scoring/                 # (keep)
  mail/                    # (keep)
```

### Frontend (incremental)

```
dashboard/
  app/                     # Add loading.tsx + error.tsx per page
  components/
    dashboard/             # (keep)
    leads/                 # (keep, absorb reply-draft-panel)
    chat/                  # (keep)
    map/                   # (keep)
    settings/              # (keep)
    notifications/         # (NEW, absorb notification-list-view)
    ai-office/             # (keep)
    layout/                # (keep)
    shared/                # (keep — only true shared primitives)
    ui/                    # (keep)
    providers/             # (keep)
    charts/                # (keep)
    performance/           # (keep)
  lib/
    api/
      leads.ts             # Split from client.ts
      outreach.ts
      pipeline.ts
      settings.ts
      ...
    hooks/                 # (keep)
  types/
    leads.ts               # Split from index.ts
    outreach.ts
    pipeline.ts
    ...
```

---

## Scoring

| Dimension | Score | Evidence |
| --- | ---: | --- |
| **Overall Structure** | **7.5** | Good domain-driven folders; services coupling and frontend SPA pattern prevent 8+ |
| **Backend Structure** | **7.5** | 10 sub-packages, clean LLM/agent layers; 98 internal commits, cross-service coupling |
| **Frontend Structure** | **6.0** | Good component hierarchy; 16/16 client pages, 982-LOC type file, 884-LOC API client |
| **Folder Consistency** | **8.0** | Very consistent snake_case/kebab-case; one naming anomaly (`dashboard_svc`) |
| **Naming Quality** | **8.0** | Clear, predictable names; some ambiguity with `outreach/` at two levels |
| **Scalability** | **7.0** | Sub-packages provide growth room; type file + API client + settings god model are bottlenecks |
| **Maintainability** | **7.0** | One model per file, extracted workflows, good tests; 131 broad excepts, 98 internal commits |
| **AI Navigation** | **8.5** | Best-in-class AGENTS.md, docs index, skills, commands; cross-service coupling is the main obstacle |
| **Human DX** | **7.5** | Makefile, docker-compose, preflight, seed, testcontainers; missing CI, storybook, loading states |

---

## Final Verdict

### Is this a 10/10 repo architecture?

**No. It is a strong 7.5/10.**

### What blocks it from 10:

1. **Transaction boundary fragmentation (blocks 8.0)** — 98 `db.commit()` calls scattered across services. No layer owns the unit of work. This is the single most impactful architectural debt.

2. **Frontend as pure client-side SPA (blocks 8.0)** — Using Next.js App Router but treating it as Create React App. Zero server components, monolithic type/API files. The framework's primary value is unused.

3. **Services layer cross-coupling (blocks 8.5)** — 40+ cross-service imports, `operational_settings_service` as universal dependency, deferred imports hiding circular references.

4. **No contract generation (blocks 9.0)** — Hand-maintained 982-LOC type file + 884-LOC API client means every backend change requires manual frontend synchronization.

5. **No CI pipeline in repo (blocks 9.5)** — Tests, linting, and type-checking exist but there's no visible automation to enforce them.

6. **Missing observability infrastructure (blocks 10.0)** — No OpenTelemetry, no distributed tracing, no invocation latency dashboards. Structured logging is present but not sufficient for an AI-heavy async system.

### What would make it a 10:

A 10/10 architecture for this codebase would have:
- Application-layer transaction coordinators (services mutate, coordinators commit)
- Server-component-first frontend with generated API types
- Split `types/index.ts` and `api/client.ts` into per-domain modules
- OpenTelemetry tracing from HTTP through Celery through Ollama
- CI pipeline enforcing tests + types + linting on every push
- Every service sub-package with a clear public API (explicit `__init__.py` exports)

The repo is **closer to 10 than most** — the foundations are sound, the domain organization is real, and the documentation is exceptional. The path from 7.5 to 9.0 is realistic with incremental refactoring. The path from 9.0 to 10.0 requires framework-level changes (server components, contract generation, observability infrastructure).
