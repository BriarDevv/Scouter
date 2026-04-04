# Scouter Refactor Roadmap

Date: 2026-04-02
Strategy: incremental, low-drama, modular-monolith hardening

## Guiding Rules

- No big-bang rewrite.
- No microservices.
- No architecture-only refactor that stalls product work for months.
- Every phase should leave the system more predictable than before.
- Prefer PRs that isolate one kind of change:
  - structural refactor,
  - contract hardening,
  - data migration,
  - behavior change.

## Phase 0: Quick Wins

### Objective

Stop the most dangerous architectural behavior immediately and add guardrails.

### Concrete changes

- Remove HTTP endpoints that rewrite `.env`.
- Introduce request id middleware and propagate correlation ids consistently.
- Add explicit warnings/flags when AI fallbacks are used.
- Add architecture guardrail tests for:
  - no new direct `.env` writes from API
  - no new private LLM helper imports outside AI infra
  - no new manual TS-only enum drift on critical DTOs
- Add a small wrapper for Redis progress access so raw key writes stop spreading.
- Fix obvious semantic mismatches:
  - one-to-one research/brief relationship declarations
  - frontend enum drift for `website_error` and `classifying`

### Expected impact

- Immediate risk reduction.
- Better diagnostics.
- Stops the architecture from getting worse while deeper refactors happen.

### Risk

Low to medium.

### Recommended order

1. Guardrail tests
2. `.env` mutation removal
3. correlation/request ids
4. fallback visibility
5. contract drift fixes

### Migrations required

- Possibly none for the quick guardrails
- small ORM/schema cleanup may require a migration if one-to-one constraints are corrected in DB shape

### API breakage

- Yes, if the crawl API-key mutation endpoint is removed or replaced
- Keep a deprecated compatibility path only if operationally necessary

### PR size

Small to medium

## Phase 1: Boundaries and Contracts

### Objective

Create real module boundaries and stop the service layer from absorbing everything.

### Concrete changes

- Introduce module-oriented packages for:
  - leads
  - pipeline
  - outreach
  - inbox
  - research
  - settings
  - notifications
  - ai
- Create application command handlers for the hottest flows first:
  - lead pipeline start
  - outreach draft generation
  - outbound send
  - inbound classification
- Move transaction ownership into those commands.
- Mark internal service commits as deprecated and reduce them step by step.
- Split DTO ownership:
  - backend API schemas stay with module API
  - frontend types become generated or imported artifacts

### Expected impact

- Lower coupling.
- Easier reasoning about "where to change what".
- Better basis for worker and frontend cleanup.

### Risk

Medium.

### Recommended order

1. Add new module shells without moving behavior yet
2. Move one vertical slice at a time
3. Deprecate old imports with temporary adapters

### Migrations required

Usually no, unless status/relationship reshaping starts here

### API breakage

Should be avoidable in this phase

### PR size

Medium

## Phase 2: Async / Pipeline Hardening

### Objective

Make workflow execution reliable, inspectable, and idempotent.

### Concrete changes

- Split `app/workers/tasks.py` into:
  - task wrappers
  - workflow orchestrators
  - supervisor flows
  - crawl execution
- Make Postgres the canonical workflow state store.
- Introduce explicit run models for batch and territory crawls if needed.
- Replace raw Redis progress truth with persisted run state.
- Implement idempotency keys per step.
- Classify step outcomes as retryable/degraded/terminal.
- Standardize retry policy and side-effect sequencing.
- Use thin Celery tasks that invoke application workflows.

### Expected impact

- Major reliability improvement.
- Lower risk of duplicate work and split-brain state.
- Easier debugging of pipeline failures.

### Risk

Medium to high.

### Recommended order

1. Create canonical run state models
2. Introduce orchestration layer
3. Move one workflow at a time:
   - full pipeline
   - batch pipeline
   - crawl
4. Remove direct Redis-driven status paths from API

### Migrations required

Likely yes

### API breakage

Possibly small status payload changes

### PR size

Medium to large, but split by workflow

## Phase 3: AI Layer Hardening

### Objective

Turn the AI layer from centralized-but-loose into typed, versioned, and observable infrastructure.

### Concrete changes

- Add AI contracts as Pydantic schemas.
- Replace regex/markdown JSON extraction for structured tasks with Ollama structured outputs where supported.
- Create a single public invocation API.
- Add prompt ids and versions.
- Add invocation persistence and metrics.
- Remove direct private LLM helper imports from workers/services.
- Model fallback/degraded outputs explicitly in domain records.

### Expected impact

- Better quality control.
- Lower debugging cost.
- Safer model/prompt evolution.

### Risk

Medium.

### Recommended order

1. Invocation envelope and prompt registry
2. Structured-output migration for one flow
3. Invocation persistence
4. Extend flow by flow

### Migrations required

Yes, if adding invocation tables / prompt version fields

### API breakage

Usually no externally; internal behavior/metadata changes yes

### PR size

Medium

## Phase 4: Observability and Testing

### Objective

Make the system operable in production and trustworthy under change.

### Concrete changes

- Add OpenTelemetry instrumentation across HTTP, Celery, HTTPX, and DB.
- Add metrics for:
  - workflow duration
  - retry counts
  - fallback rate
  - provider error rates
  - queue latency
- Add PostgreSQL integration test lane.
- Add Alembic migration smoke tests.
- Add Redis/Celery integration tests for critical flows.
- Keep SQLite only for pure unit-speed tests if still useful.

### Expected impact

- Huge reduction in blind debugging.
- Better release confidence.

### Risk

Medium.

### Recommended order

1. tracing foundation
2. Postgres test lane
3. migration tests
4. async integration tests

### Migrations required

Not necessarily, unless observability tables are added

### API breakage

No

### PR size

Small to medium

## Phase 5: Frontend Contract Cleanup

### Objective

Eliminate manual contract drift and reduce client-side accidental complexity.

### Concrete changes

- Generate API types/client from OpenAPI.
- Replace manually duplicated critical enums and DTOs.
- Move read-heavy pages to server components where practical.
- Break god pages into route sections and feature modules.
- Introduce a consistent cache/invalidation strategy.

### Expected impact

- Faster frontend evolution.
- Fewer silent UI mismatches.
- Better App Router usage.

### Risk

Medium.

### Recommended order

1. generated contracts
2. retrofit existing client wrappers or replace them
3. migrate the worst pages:
   - lead detail
   - settings
   - panel

### Migrations required

No

### API breakage

Should be avoidable if backend contracts stay stable

### PR size

Medium

## Phase 6: DX and Infra Polish

### Objective

Make the repo easier to run, test, onboard, and deploy with less ambiguity.

### Concrete changes

- Separate dev and prod container posture.
- Move from implicit environment assumptions to documented profiles.
- Add reproducible test/dev commands that do not depend on hidden local state.
- Add architecture lint or import-boundary checks.
- Add ADR index and repo-level architecture docs.

### Expected impact

- Better onboarding.
- Less operational surprise.
- Architecture stays healthier over time.

### Risk

Low.

### Recommended order

1. docs + profiles
2. boundary checks
3. image/build polish

### Migrations required

No

### API breakage

No

### PR size

Small

## Suggested ADRs

Write these early. They will force the architecture to become explicit.

1. ADR: Scouter remains a modular monolith
2. ADR: PostgreSQL is the canonical workflow state store; Redis is not source of truth
3. ADR: Transaction ownership lives in application commands, not inner services
4. ADR: Lead lifecycle status is split from pipeline stage
5. ADR: AI invocations use typed contracts and prompt versioning
6. ADR: Frontend contracts are generated from backend schemas
7. ADR: Runtime policy, deploy config, and secrets are separate configuration classes
8. ADR: Notification intent and notification transport are decoupled
9. ADR: Batch and crawl supervision are modeled as first-class workflow runs
10. ADR: PostgreSQL integration tests and Alembic migration tests are mandatory for workflow-sensitive changes

## Suggested Commit Strategy

Use commits that are structurally honest. Do not mix refactor and behavior changes unless the behavior change is the reason the refactor exists.

Recommended commit style:

- `chore(arch): add workflow/request correlation ids`
- `refactor(pipeline): extract orchestration service from celery task wrappers`
- `refactor(settings): remove env mutation from HTTP surface`
- `feat(ai): add structured invocation contracts for lead-quality flow`
- `test(db): add postgres transaction fixture with savepoints`
- `build(frontend): generate api types from openapi`

## Suggested PR Strategy

### Small PRs

Use for:

- removing dangerous endpoints
- adding middleware
- adding guardrail tests
- fixing enum drift
- adding tracing hooks
- adding ADRs/docs

### Medium PRs

Use for:

- extracting one workflow slice into a new module
- introducing generated API contracts
- introducing AI invocation envelopes
- adding Postgres integration fixtures

### Large PRs

Only when unavoidable, and still split by architectural seam:

- lead state split (`LeadLifecycleStatus` vs `LeadPipelineStage`)
- canonical workflow state redesign
- replacement of Redis progress truth with persisted run models

### Recommended PR order

1. docs + guardrails + dangerous endpoint removal
2. correlation ids + observability foundations
3. generated contracts on frontend/backend boundary
4. pipeline orchestration extraction
5. canonical workflow state redesign
6. AI structured invocation layer
7. Postgres/Alembic/Celery integration test hardening

## What Not To Do

- Do not start by renaming every folder in the repo.
- Do not introduce repositories/interfaces everywhere before choosing the hot workflows.
- Do not convert this into microservices.
- Do not rebuild the dashboard while backend contracts are still unstable.
- Do not replace Celery before fixing workflow ownership.
