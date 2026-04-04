# Scouter Architecture Audit

Date: 2026-04-02
Auditor: Codex acting as Principal Architect / Staff Engineer
Scope: backend, workers, LLM layer, frontend contracts, infra, DX, testing, security

## Methodology

- Full repo walk and structural inventory.
- Focused code inspection of backend entrypoints, services, models, workers, LLM modules, frontend pages/hooks/client, infra, tests, and migrations.
- Complexity sampling with repo-level metrics.
- Contrast against official/current stack guidance where materially relevant.

## Evidence Snapshot

- 117 API route handlers.
- 277 functions under `app/services/`.
- 16 Celery tasks.
- 85 `db.commit()` calls inside `app/services` and `app/workers`.
- 91 broad `except Exception` catches inside `app/`.
- 61 `"use client"` directives across `dashboard/app` and `dashboard/components`.
- 187 tests collected successfully via `.venv/bin/python -m pytest --collect-only -q`.
- A full `pytest -q` run started and produced progress, but did not complete within the observation window, so runtime test claims below are based on collection plus targeted code inspection, not a clean full-pass execution.

## Executive Summary

Scouter is not a bad codebase. It is also not an architecturally excellent one.

It is a feature-rich modular monolith with several good foundations:

- a real domain split by folders instead of a flat pile of files,
- a centralized LLM client/resolver,
- persisted task/pipeline tracking,
- a coherent operational dashboard,
- a non-trivial test suite,
- structured logging and basic metrics.

The problem is that the architecture is now bending under its own success.

The dominant failure mode is not "missing features" but "responsibilities collapsing into the same layers". `services/` behaves like a god layer, `app/workers/tasks.py` behaves like a workflow god module, routers sometimes leak infrastructure and configuration mutation, the frontend manually mirrors backend contracts and is already drifting, and transaction boundaries are weak enough that retries, partial failures, and state divergence are real architectural risks.

The project is in the dangerous middle stage:

- beyond prototype,
- clearly useful,
- still operable by one person,
- but already carrying enough entropy that scaling features without structural hardening will get slower, riskier, and more expensive.

My blunt verdict:

- Product direction: strong.
- Codebase ambition: strong.
- Architectural discipline: inconsistent.
- Long-term maintainability without refactor: poor.

## Architecture Score

Global score: **5.6 / 10**

### Scorecard by dimension

| Dimension | Score | Verdict |
| --- | ---: | --- |
| Modularity | 6.0 | Better than average repo structure, but boundaries are porous. |
| Layer separation | 4.0 | Weak. Too much logic leaks across routers, services, tasks, and providers. |
| Domain model | 5.0 | Serviceable, but status/state boundaries are blurry and some relations are semantically wrong. |
| Async reliability | 4.5 | Celery exists and is used seriously, but orchestration/idempotency/state tracking are only partially hardened. |
| AI architecture | 6.0 | Centralized and intentional, but not yet strongly contracted, versioned, or observable. |
| Observability | 4.5 | Better than nothing, well short of production-grade distributed operability. |
| Security | 4.5 | There is sanitization and some secret handling, but several architectural boundaries are too weak. |
| Frontend/backend contracts | 4.0 | Manual contracts are drifting already. |
| DX | 6.5 | Local scripts and repo organization help, but test realism and operational consistency lag. |
| Scalability | 5.5 | Modular monolith can scale further, current workflow design will become a tax. |
| Maintainability | 4.5 | Too many hot spots and too much hidden coupling. |

## Current Architecture Map

### Entrypoints

- HTTP API: `app/main.py` + `app/api/router.py` -> 20+ REST/webhook/chat routers.
- SSE chat: `app/api/v1/chat.py` -> `app/agent/core.py`.
- External webhooks: WhatsApp, Telegram.
- Async workers: `app/workers/celery_app.py`, `app/workers/tasks.py`, `app/workers/brief_tasks.py`.
- Periodic maintenance: `app/workers/janitor.py`.
- Frontend: Next.js App Router under `dashboard/app`.
- Local operations: `Makefile`, `scripts/*.sh`, Docker Compose.

### Core business flows

- Lead ingestion:
  `crawl -> create_lead -> enrich -> score -> analyze -> high-lane research -> brief -> review -> draft`.
- Outreach:
  `draft -> review/approval -> send -> delivery log -> notification`.
- Inbound mail/reply assistant:
  `sync inbox -> match thread/lead -> classify -> reviewer pass -> generate reply draft -> send`.
- Agent chat:
  `conversation -> streamed Ollama response -> tool execution -> persisted tool calls/messages`.

### Bounded contexts actually present

The repo is not pure layered architecture, but these bounded contexts are visible:

- Lead acquisition and qualification.
- Research and commercial briefing.
- Outreach and delivery.
- Inbound mail and reply assistance.
- Operational control plane (settings, notifications, leader dashboard).
- AI orchestration and prompting.
- Territory crawling.
- Multi-channel operator chat/agent.

The problem is not absence of contexts. The problem is that the contexts do not have strong enough boundaries in implementation.

### Data flow and state flow

- PostgreSQL is the main business source of truth.
- Redis is used both as Celery broker/backend and as ad hoc workflow progress storage.
- Ollama is called synchronously from services/workers for summaries, evaluation, review, dossier, brief, and reply generation.
- External comms/providers:
  SMTP, IMAP, Kapso, Telegram, CallMeBot-style WhatsApp alerts, Google Maps API, generic website fetches, Instagram scraping.

### Async architecture as implemented

- `task_full_pipeline` dispatches only the first task.
- Individual tasks chain to the next using `.delay()`.
- `TaskRun` and `PipelineRun` track persisted workflow execution.
- Batch pipeline and territory crawl keep separate progress documents in Redis.
- Some workflows bypass reusable async steps and execute synchronous service logic inline.

### Main complexity hot spots

- `app/workers/tasks.py` (1819 LOC).
- `app/llm/client.py` (845 LOC).
- `dashboard/lib/api/client.ts` (699 LOC).
- `dashboard/types/index.ts` (855 LOC).
- `dashboard/app/leads/[id]/page.tsx` (1263 LOC).
- `app/services/inbound_mail_service.py` (614 LOC).
- `app/api/v1/settings.py` (322 LOC).

## Findings

### Critical 1: Transaction boundaries are fragmented and unsafe

- Severity: Critical
- Impact: inconsistent state, duplicate side effects, hard-to-reproduce retries, weak testability
- Evidence:
  - 85 internal `db.commit()` calls across `app/services` and `app/workers`
  - `app/services/lead_service.py`
  - `app/services/enrichment_service.py`
  - `app/services/scoring_service.py`
  - `app/services/outreach_service.py`
  - `app/services/brief_service.py`
  - `app/services/notification_service.py`
  - `app/workers/tasks.py`
- Why this is a problem:
  - The caller rarely owns the unit of work.
  - A single business action spans multiple commits and side effects.
  - Celery retries under `acks_late=True` become materially riskier if half the state committed before a crash.
  - Services become difficult to compose because each service implicitly decides persistence and transaction timing.
- Exact recommendation:
  - Move to explicit application-level transaction boundaries.
  - Make domain/application services mutate the session and return results; commit in command handlers or dedicated workflow coordinators.
  - Introduce a small number of orchestration commands, for example:
    - `LeadPipelineCommands.run_enrichment(...)`
    - `LeadPipelineCommands.run_scoring(...)`
    - `OutreachCommands.generate_draft(...)`
    - `InboxCommands.classify_reply(...)`
  - Keep Celery tasks thin: load command -> execute -> mark result.
  - Reserve `commit()` for explicit boundary owners, not inner services.

### Critical 2: Workflow orchestration is concentrated in a god module and partially duplicated

- Severity: Critical
- Impact: async fragility, change fear, duplicated business rules, slow onboarding
- Evidence:
  - `app/workers/tasks.py` is 1819 LOC
  - It mixes:
    - workflow dispatch,
    - step execution,
    - tracking,
    - Redis progress documents,
    - crawl ingestion,
    - LLM analysis,
    - research/dossier/brief chaining,
    - batch control logic
  - `task_batch_pipeline` duplicates enrichment/scoring/analysis/research/brief/draft logic inline instead of reusing workflow primitives.
- Why this is a problem:
  - This file is an accidental orchestration framework with no clean abstraction.
  - Every new branch in the pipeline increases coupling to tracking, Redis, Celery, and business services.
  - Reliability fixes and feature work collide in the same module.
- Exact recommendation:
  - Split orchestration into a dedicated pipeline module.
  - Keep Celery task definitions extremely small and delegate to workflow coordinators.
  - Separate:
    - lead-step executors,
    - pipeline state transitions,
    - batch/crawl supervisors,
    - provider integrations.
  - Replace "tasks calling tasks with embedded business decisions" with either:
    - a workflow coordinator that dispatches next steps from persisted pipeline state, or
    - Celery canvas primitives where the flow is linear and stable.

### Critical 3: Runtime state has no single source of truth

- Severity: Critical
- Impact: UI/status drift, stop/resume ambiguity, operational confusion, brittle recovery
- Evidence:
  - `app/models/task_tracking.py` stores `PipelineRun` and `TaskRun`
  - `app/api/v1/pipelines.py` also stores batch state in Redis
  - `app/api/v1/crawl.py` also stores crawl state in Redis
  - `app/workers/tasks.py` writes many `pipeline:batch` and `crawl:territory:*` keys directly
- Why this is a problem:
  - There are two state systems:
    - persisted run/task state in Postgres,
    - ephemeral workflow progress state in Redis.
  - They have different semantics and lifetimes.
  - Operators can see one system say "running" while the other says "failed/stale/idle".
- Exact recommendation:
  - Make Postgres the canonical source of workflow state.
  - Keep Redis only for broker/backend, ephemeral locks, and maybe short-lived caches.
  - Add explicit persisted state models for batch/crawl supervisors or extend `PipelineRun`.
  - Expose frontend status from one read model, not from raw Redis keys.

### Critical 4: Configuration and secret boundaries are architecturally unsafe

- Severity: Critical
- Impact: secret leakage risk, operational mistakes, unclear authority of config, poor compliance posture
- Evidence:
  - `app/api/v1/crawl.py` writes `.env` from an API endpoint
  - `app/core/crypto.py` derives credential encryption from `SECRET_KEY`
  - `decrypt_safe()` returns the original value on invalid token
  - `app/api/v1/settings.py` mixes runtime policy, credential CRUD, connectivity tests, and webhook registration
  - `app/mail/imap_provider.py` reads env settings directly, bypassing DB effective settings
- Why this is a problem:
  - Deploy-time config, runtime policy, and secrets are mixed into one mutable control plane.
  - A web API should not rewrite deployment files.
  - Using one app secret as the root for other credential encryption is a weak boundary.
  - Returning plaintext on decryption failure can silently mask key rotation or corruption issues.
- Exact recommendation:
  - Split config into:
    - immutable deploy config from env,
    - mutable runtime policy in DB,
    - credentials in a dedicated secret store abstraction.
  - Remove `.env` mutation through HTTP entirely.
  - Introduce a dedicated encryption key version for stored credentials.
  - Make decryption failure explicit and observable.
  - Centralize all effective credential resolution in one adapter layer.

### High 1: `services/` is acting as a god layer

- Severity: High
- Impact: hidden coupling, low cohesion, rising cognitive load
- Evidence:
  - 277 functions under `app/services`
  - 17 direct service-to-service imports
  - representative cross-coupling:
    - `mail_service -> outreach_service`
    - `reply_send_service -> inbound_mail_service`, `mail_service`
    - `notification_service -> whatsapp_service`, `telegram_service`
    - `leader_service -> dashboard_service`
    - `settings_service -> inbound_mail_service`, `mail_credentials_service`, `operational_settings_service`
- Why this is a problem:
  - "Service" has become the dumping ground for both application orchestration and business logic.
  - This produces a false sense of layering while actual dependencies remain tangled.
- Exact recommendation:
  - Break `services/` into explicit module-level packages with application/domain/infrastructure intent.
  - Example:
    - `modules/leads/application/...`
    - `modules/leads/domain/...`
    - `modules/leads/infra/...`
  - Use service names for actual responsibilities, not as a blanket category.

### High 2: Domain state is under-modeled and semantically blurred

- Severity: High
- Impact: unclear business invariants, brittle UI assumptions, wrong aggregate ownership
- Evidence:
  - `app/models/lead.py` uses `LeadStatus` for both processing stages and CRM lifecycle states
  - `app/models/research_report.py` has `lead_id unique=True` but `Lead.research_reports` is modeled as a list
  - `app/models/commercial_brief.py` has `lead_id unique=True` but `Lead.commercial_briefs` is modeled as a list
  - `app/services/lead_service.py` computes dedup from `website_url`, while model comments and project docs talk about domain normalization
- Why this is a problem:
  - One enum is carrying two unrelated concepts:
    - automated processing stage,
    - commercial lifecycle.
  - Relationship cardinality should reflect truth; right now the ORM shape lies about the business shape.
  - Dedup policy drift means the business rule is not stable enough to trust.
- Exact recommendation:
  - Split current lead state into at least:
    - `lifecycle_status`
    - `pipeline_stage`
    - optionally `qualification_band`
  - Make research/brief relationships explicitly one-to-one if that is the intended rule.
  - Extract dedup normalization into a single policy object with test coverage against real URL/domain cases.

### High 3: AI architecture is centralized but not strongly contracted

- Severity: High
- Impact: fragile parsing, silent degradation, weak auditability, hard model evolution
- Evidence:
  - `app/llm/client.py` relies on `_extract_json()` heuristics
  - many helpers catch broad exceptions and return synthetic fallback payloads
  - `app/workers/brief_tasks.py` imports private `_call_ollama_chat` and `_extract_json` directly
  - no dedicated model invocation table with prompt version, latency, fallback_used, or structured validation outcome
- Why this is a problem:
  - Centralization alone is not enough.
  - Without typed request/response contracts, prompt versioning, and invocation logging, the AI layer is hard to debug and expensive to trust.
  - Silent fallbacks keep the pipeline moving, but can hide degraded quality while appearing "successful".
- Exact recommendation:
  - Create a formal AI execution layer:
    - typed request/response contracts via Pydantic,
    - prompt registry with explicit versions,
    - single public invocation API,
    - persisted invocation metadata,
    - explicit degraded/fallback status.
  - Use Ollama structured outputs with JSON schema instead of regex-based JSON extraction for structured tasks.
  - Ban direct use of private LLM helpers from workers/services.

### High 4: Frontend contracts are manual and already drifting

- Severity: High
- Impact: UI bugs, hidden data loss, slower evolution, duplicated maintenance cost
- Evidence:
  - `dashboard/lib/api/client.ts` is a hand-maintained 699 LOC client
  - `dashboard/types/index.ts` is a hand-maintained 855 LOC type file
  - drift already present:
    - backend `SignalType.WEBSITE_ERROR` missing from frontend `SignalType`
    - backend inbound status includes `classifying`, frontend type omits it
  - some types live in `dashboard/types/index.ts`, others in `dashboard/lib/api/client.ts`
- Why this is a problem:
  - Manual type mirrors eventually rot.
  - The repo already has proof of drift; this is not hypothetical.
- Exact recommendation:
  - Generate TS contracts from FastAPI OpenAPI/Pydantic schemas or from shared schema artifacts.
  - Keep one ownership source for DTOs.
  - Add CI contract drift checks.

### High 5: App Router is being used mostly as a client-side SPA shell

- Severity: High
- Impact: avoidable client complexity, weaker cache model, unnecessary browser work, poorer data discipline
- Evidence:
  - 61 `"use client"` directives in app/components
  - `dashboard/app/leads/[id]/page.tsx` is a 1263 LOC client page with manual `Promise.all`
  - `dashboard/lib/hooks/use-page-data.ts` is a minimal client fetch hook with no shared cache/invalidation
  - no evidence of TanStack Query/SWR or serious server-component-first data loading
- Why this is a problem:
  - Next App Router defaults to server components for a reason.
  - Scouter is operational software with many read-heavy screens; pushing most page composition to the client is unnecessary and costly.
- Exact recommendation:
  - Move read-heavy route shells to server components by default.
  - Keep client islands only for live controls, polling widgets, chat, and interactive mutations.
  - Introduce a consistent cache/invalidation strategy.

### High 6: `OperationalSettings` is absorbing too much responsibility

- Severity: High
- Impact: unclear ownership, accidental coupling, hard migrations, policy drift
- Evidence:
  - `app/models/settings.py` is a large singleton with runtime mode, brand context, automation toggles, thresholds, review policy, mail behavior, pricing matrix, notification thresholds, and more
  - `app/services/operational_settings_service.py` contains large field maps and mode presets
  - `settings.py` API router acts as a control plane for multiple unrelated concerns
- Why this is a problem:
  - A giant singleton settings row is not modularity; it is centralized accidental coupling.
  - Every new feature wants to stuff one more field into it.
- Exact recommendation:
  - Split runtime policy into bounded policy groups:
    - `pipeline_policy`
    - `outreach_policy`
    - `reply_policy`
    - `branding_profile`
    - `notification_policy`
  - Keep deploy config out of this model entirely.

### High 7: Observability is present but not operationally sufficient

- Severity: High
- Impact: long MTTR, hard incident reconstruction, opaque AI/provider failures
- Evidence:
  - good baseline:
    - `app/core/logging.py`
    - Prometheus instrumentator in `app/main.py`
    - `PipelineRun` and `TaskRun`
  - gaps:
    - no clear HTTP request id middleware
    - no distributed tracing across HTTP -> Celery -> LLM -> provider calls
    - no durable model invocation logs
    - no canonical workflow event stream or audit ledger
- Why this is a problem:
  - You can inspect pieces of the system, but not follow a full causal chain reliably.
  - AI-heavy asynchronous systems need stronger provenance than ordinary CRUD apps.
- Exact recommendation:
  - Add request/pipeline/task correlation as first-class tracing data.
  - Add OpenTelemetry tracing across API, Celery, HTTPX, and provider adapters.
  - Persist workflow and model invocation events with explicit statuses.

### High 8: Test strategy creates false confidence on database behavior

- Severity: High
- Impact: production-only bugs, migration blind spots, locking/index semantics missed
- Evidence:
  - `tests/conftest.py` forces `sqlite:///./test.db`
  - tables are created via `Base.metadata.create_all()`
  - tests do not validate Alembic migrations against PostgreSQL
  - partial indexes, enum semantics, JSON behavior, locking, and transaction semantics differ from Postgres 16
- Why this is a problem:
  - SQLite is acceptable for unit-level speed, but not as the main correctness oracle for a PostgreSQL system.
  - The architecture relies on DB semantics that SQLite does not faithfully represent.
- Exact recommendation:
  - Keep lightweight SQLite tests only for pure unit boundaries if desired.
  - Add a PostgreSQL integration test lane using transactional rollback/savepoint patterns.
  - Add migration smoke tests on real Postgres.
  - Add Redis/Celery integration tests for key async flows.

### Medium 1: Routers are not consistently thin

- Severity: Medium
- Impact: weaker API boundaries, more duplication, infra leakage
- Evidence:
  - `app/api/v1/crawl.py` uses Redis directly and rewrites `.env`
  - `app/api/v1/pipelines.py` uses Redis directly for control state
  - `app/api/v1/settings.py` performs HTTP connectivity tests and Telegram webhook registration logic
  - `app/api/v1/leads.py` runs research synchronously from the router
- Why this is a problem:
  - Routers should validate/translate HTTP, not own provider behavior and runtime mutation semantics.
- Exact recommendation:
  - Move non-HTTP concerns into application commands and provider adapters.
  - Make routers map request -> command -> response.

### Medium 2: Notification and channel delivery concerns are entangled

- Severity: Medium
- Impact: harder policy changes, unexpected sync latency, notification side effects in business transactions
- Evidence:
  - `app/services/notification_service.py` creates notifications and dispatches WhatsApp/Telegram inline
  - external notification delivery is mixed with notification persistence
- Why this is a problem:
  - Notification creation and notification transport are distinct concerns.
  - Inline provider dispatch increases coupling and can slow or destabilize the transaction path.
- Exact recommendation:
  - Persist notification intent first.
  - Deliver externally via separate async transport handlers or an outbox-driven dispatcher.

### Medium 3: Agent/chat execution keeps too much operational responsibility inside the request path

- Severity: Medium
- Impact: long-lived DB sessions, harder streaming resilience, cross-channel ambiguity
- Evidence:
  - `app/api/v1/chat.py` streams SSE while passing a request DB session into `run_agent_turn`
  - `app/agent/core.py` saves messages/tool calls and executes tools in the same loop
  - `app/agent/channel_router.py` can reuse the most recent active conversation across non-web channels
- Why this is a problem:
  - Streaming + tool execution + persistence + long-lived session management is a delicate mix.
  - Cross-channel conversation reuse is convenient, but the current rule is broad enough to risk context bleed.
- Exact recommendation:
  - Move agent persistence and tool execution into explicit turn/application services.
  - Shorten session scope per persistence boundary.
  - Make cross-channel conversation linking explicit, not "latest active conversation".

### Medium 4: Frontend maintainability is being hurt by god pages and god clients

- Severity: Medium
- Impact: slower UI changes, harder testing, repeated fetch choreography
- Evidence:
  - `dashboard/app/leads/[id]/page.tsx` is 1263 LOC
  - `dashboard/lib/api/client.ts` concentrates almost all endpoint wrappers
- Why this is a problem:
  - The frontend currently scales by accretion, not by composition.
- Exact recommendation:
  - Split route-level orchestration from view sections.
  - Group client calls per domain or generated SDK namespace.

### Medium 5: Error handling often hides degradation instead of modeling it

- Severity: Medium
- Impact: "green but wrong" system behavior, poor diagnosis
- Evidence:
  - 91 broad `except Exception` catches across `app/`
  - many LLM helpers return fallback objects that look valid enough to continue
  - several `except Exception: pass` patterns exist in orchestration paths
- Why this is a problem:
  - Silent degradation is often worse than explicit failure in AI-heavy workflow software.
- Exact recommendation:
  - Classify failures into:
    - retryable,
    - degraded-but-usable,
    - terminal.
  - Persist the degradation status explicitly.

### Low 1: Python version posture is inconsistent with the stated target

- Severity: Low
- Impact: toolchain drift, unclear modernization target
- Evidence:
  - `pyproject.toml` requires `>=3.12,<3.15`
  - Ruff and mypy target `py312`
- Why this is a problem:
  - If the architectural target is Python 3.14, the repo is not yet expressing that discipline.
- Exact recommendation:
  - Decide the true baseline and align lint/type/test/runtime images with it.

### Low 2: Naming and transport semantics need cleanup

- Severity: Low
- Impact: confusion more than breakage
- Evidence:
  - WhatsApp response flow uses `send_alert` semantics in places
  - `recipient_email` is reused for WhatsApp delivery shape
- Why this is a problem:
  - Semantic mismatch accumulates cognitive debt.
- Exact recommendation:
  - Normalize transport-neutral delivery naming or split channel-specific DTOs.

### Low 3: Local infra is useful but not sharply separated between dev and production posture

- Severity: Low
- Impact: deployment ambiguity
- Evidence:
  - `docker-compose.yml` runs API with `--reload`
  - images are practical for development, less opinionated for production hardening
- Why this is a problem:
  - The project is operationally serious enough to benefit from clearer dev/prod boundaries.
- Exact recommendation:
  - Keep Compose for local/dev.
  - Add a distinct production Compose/profile or deployment manifests with hardened defaults.

## Real Strengths

- Clear product shape and real operational use cases.
- Domain folders already exist; this is not a flat script heap.
- Centralized LLM model resolution is a strong starting point.
- Prompt injection defense is intentional and tested.
- Persisted `PipelineRun` / `TaskRun` gives a real workflow backbone.
- Dashboard is aligned to operator workflows, not only CRUD screens.
- The test suite breadth is meaningful, even if environment realism is insufficient.

## Real Weaknesses

- Weak boundary ownership.
- Too many internal commits.
- Async orchestration too coupled to Celery task files.
- Manual contract duplication.
- Configuration/control plane over-centralization.
- Insufficient operational truth model for multi-step workflows.

## Risks That Matter Most

- Duplicate or inconsistent side effects during retries and partial failures.
- Control plane mistakes caused by mutable config/secrets exposure.
- Silent AI degradation being treated as successful work.
- UI/contract divergence hidden by manual TS types.
- Production-only DB/workflow bugs escaping SQLite-based tests.

## Conceptual Bottlenecks

- `services/` as the universal layer.
- `app/workers/tasks.py` as the implicit workflow engine.
- `OperationalSettings` as a catch-all policy store.
- `dashboard/lib/api/client.ts` and `dashboard/types/index.ts` as manual contract bottlenecks.

## Areas That Are Overdesigned

- Giant operational settings singleton as a pseudo control plane.
- Broad chat/agent tool surface before stronger module boundaries and observability exist.
- Multi-channel notification routing embedded directly into core service paths.

## Areas That Are Underdesigned

- Transaction ownership and unit-of-work boundaries.
- Workflow/event modeling.
- AI invocation contracts, prompt versioning, and traceability.
- Frontend/backend contract generation.
- Postgres-realistic test strategy.
- End-to-end observability.

## Decisions I Would Keep

- Stay a modular monolith.
- Keep FastAPI + Celery + Redis + PostgreSQL for now.
- Keep a centralized AI model catalog/resolver.
- Keep persisted pipeline/task tracking, but strengthen it.
- Keep the operational dashboard orientation.

## Decisions I Would Change Without Hesitation

- Internal commits inside business services.
- Direct task-to-task orchestration embedded in large worker modules.
- `.env` mutation through API.
- Manual TS contract mirrors as the primary contract strategy.
- Overloaded `LeadStatus`.
- Mixed env/runtime/secret control plane in one surface.

## External Contrast With Primary Sources

These sources support the main architectural recommendations:

- SQLAlchemy transaction scope and context-managed session boundaries:
  https://docs.sqlalchemy.org/en/21/orm/session_transaction.html
- SQLAlchemy savepoint-based test isolation on real databases:
  https://docs.sqlalchemy.org/en/21/orm/session_transaction.html
- Celery guidance on idempotent tasks, acknowledgements, and retries:
  https://docs.celeryq.dev/en/v5.1.1/userguide/tasks.html
  https://docs.celeryq.dev/en/3.1/userguide/tasks.html
- Next.js App Router and Server Components as the default model:
  https://nextjs.org/docs/app
  https://nextjs.org/docs/14/app/building-your-application/rendering/server-components
- Ollama structured outputs using JSON schema:
  https://ollama.com/blog/structured-outputs
