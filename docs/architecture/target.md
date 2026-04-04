# Scouter Target Architecture

> **Staleness note (2026-04-04):** Written before Agent OS. Many targets here (workflow discipline, contract boundaries, test coverage) have been partially or fully achieved. Read with that context.

Date: 2026-04-02
Goal: move Scouter from a feature-rich modular monolith with porous boundaries to a pragmatic, operable, AI-first modular monolith with strong workflow and contract discipline.

## Design Principles

- Keep the monolith. Do not split into microservices.
- Make module boundaries real in code, not just in folders.
- Move transaction ownership up to application commands/workflows.
- Make PostgreSQL the canonical workflow state store.
- Use Celery as an execution substrate, not as the place where business architecture lives.
- Make AI invocations typed, versioned, observable, and explicitly degraded when needed.
- Reduce accidental complexity before adding new abstractions.
- Optimize for one team or one serious maintainer, not for org-chart theater.

## What "Excellent" Looks Like Here

For Scouter, architecturally excellent does not mean:

- microservices,
- CQRS everywhere,
- event sourcing,
- a distributed saga engine,
- or a hyper-pure DDD implementation.

It means:

- a modular monolith with obvious boundaries,
- explicit workflow orchestration,
- typed contracts across backend/workers/frontend,
- clear separation of deploy config, runtime policy, and secrets,
- strong operational traces for AI-heavy async flows,
- and a test strategy that matches production reality.

## Recommended Module Structure

This is a target shape, not a mandatory one-shot rename:

```text
app/
  bootstrap/
    api.py
    worker.py
    config.py
    logging.py
    telemetry.py

  shared/
    db/
      base.py
      session.py
      uow.py
    ids/
    types/
    errors/
    events/
    security/
    utils/

  interfaces/
    http/
      api/
        leads.py
        outreach.py
        inbox.py
        pipeline.py
        settings.py
        dashboards.py
      deps.py
      middleware.py
    webhooks/
      whatsapp.py
      telegram.py
    agent/
      chat_api.py
      channel_router.py

  modules/
    leads/
      domain/
        models.py
        enums.py
        policies.py
        dedup.py
      application/
        commands.py
        queries.py
        dto.py
      infra/
        repo.py
        mappers.py
      api/
        schemas.py

    pipeline/
      domain/
        models.py
        enums.py
        state_machine.py
      application/
        commands.py
        orchestrators.py
        events.py
      infra/
        repo.py
        celery_dispatch.py
        progress_store.py
      api/
        schemas.py

    research/
      domain/
      application/
      infra/
      api/

    outreach/
      domain/
      application/
      infra/
      api/

    inbox/
      domain/
      application/
      infra/
      api/

    territories/
      domain/
      application/
      infra/
      api/

    notifications/
      domain/
      application/
      infra/
      api/

    settings/
      domain/
      application/
      infra/
      api/

    ai/
      contracts/
      prompts/
      application/
        invocations.py
        policies.py
      infra/
        ollama_client.py
        prompt_registry.py
        invocation_repo.py

    comms/
      email/
      whatsapp/
      telegram/
      web_fetch/
      crawling/
```

## Boundary Rules

### 1. Interfaces

- HTTP routers, webhooks, and agent transport adapters live here.
- They translate transport concerns only:
  - auth,
  - request validation,
  - response mapping,
  - streaming framing.
- They do not:
  - write `.env`,
  - talk to Redis directly for business state,
  - own retry logic,
  - or build provider-specific orchestration.

### 2. Application layer

- Owns use cases, commands, queries, and transaction boundaries.
- Calls repositories, domain policies, provider adapters, and AI invocation APIs.
- This is where the unit of work lives.
- This is also where "what happens next" should be decided.

### 3. Domain layer

- Owns business vocabulary and invariants.
- No HTTP, no Celery, no Redis, no provider SDK assumptions.
- Good candidates:
  - lead lifecycle rules,
  - dedup normalization,
  - scoring rules,
  - qualification policies,
  - draft approval rules,
  - suppression rules.

### 4. Infrastructure layer

- ORM repos, provider adapters, Redis locks/caches, SMTP/IMAP/Kapso/Telegram/Ollama clients, crawler adapters.
- Infra implements interfaces required by application logic.

## Domain Model Redesign

### Lead state

Current `LeadStatus` is overloaded. Split it.

Recommended:

- `LeadLifecycleStatus`
  - `new`
  - `contacted`
  - `opened`
  - `replied`
  - `meeting`
  - `won`
  - `lost`
  - `suppressed`
- `LeadPipelineStage`
  - `ingested`
  - `enriched`
  - `scored`
  - `analyzed`
  - `researched`
  - `briefed`
  - `drafted`
  - `reviewed`
- `LeadQualification`
  - `high`
  - `medium`
  - `low`
  - `unknown`

This removes the worst ambiguity in the system.

### Research and brief cardinality

Pick one truth and model it honestly:

- If there is only one current report/brief per lead, use one-to-one explicitly.
- If versions matter, introduce `version`, `is_current`, and query helpers.

Pragmatic recommendation:

- Make them explicit one-to-one now.
- If later you want historical regeneration, add versioned snapshots then.

### Processing state

Introduce a dedicated workflow state model instead of overloading lead rows plus Redis keys:

- `PipelineRun`
- `PipelineStepRun`
- optional `BatchRun`
- optional `TerritoryCrawlRun`

Each should have:

- canonical status,
- step name,
- parent/root ids,
- idempotency key,
- correlation id,
- timestamps,
- error classification,
- small structured result payload,
- optional links to produced artifacts.

## Workflow and Celery Architecture

### What should change

Today, Celery tasks are doing too much. Target pattern:

- Application command owns the workflow transition.
- Celery task is a thin execution wrapper around that command.
- Progress and state are persisted in Postgres.
- Redis is optional for lock/cache acceleration only.

### Recommended orchestration model

#### For lead processing

```text
HTTP/API or batch supervisor
  -> create PipelineRun
  -> dispatch first executable step
  -> each step writes canonical result
  -> orchestrator decides next transition from persisted state
  -> terminal state marks run completed/failed/degraded
```

#### For batch and crawl supervision

- Model them as first-class runs, not as Redis-only progress documents.
- Stop/retry/cancel act on persisted run commands.

### Idempotency model

Each step should be idempotent by explicit policy:

- unique idempotency key per `(entity, step, version)`
- optimistic or advisory lock around step execution
- terminal result persisted once
- side effects either:
  - happen after durable state update, or
  - use an outbox table

### Error model

Every failure should be classified:

- `retryable`
- `degraded`
- `terminal`
- `cancelled`

This is materially better than "exception happened, maybe fallback, maybe warning".

### When to use Celery canvas

Use Celery chain/group/chord only where the flow is structurally simple and stable.

- Good fit:
  - linear, stateless step chains
  - fan-out review or enrichment subtasks
- Bad fit:
  - deep business branching encoded directly into Celery signatures

The real workflow logic should still live in application orchestrators.

## AI / LLM Target Architecture

## Goals

- No more regex-first parsing for structured tasks.
- No more direct private LLM helper imports.
- No more silent success that is actually fallback output.

### Recommended shape

```text
modules/ai/
  contracts/
    lead_quality.py
    outreach_draft.py
    reply_review.py
    dossier.py
    commercial_brief.py
  prompts/
    registry.py
    versions.py
    templates/
  application/
    invoke.py
    policies.py
  infra/
    ollama_client.py
    invocation_repo.py
```

### Core API

One public invocation surface, for example:

```python
invoke_structured(
    role=LLMRole.EXECUTOR,
    prompt_id="lead_quality.v3",
    schema=LeadQualityResult,
    system_inputs=...,
    user_inputs=...,
    timeout=...,
    tags={"lead_id": ..., "pipeline_run_id": ...},
)
```

Return a typed result envelope:

- `status`
- `parsed`
- `raw_output`
- `model`
- `prompt_version`
- `latency_ms`
- `fallback_used`
- `error_type`

### Persisted invocation metadata

Add a lightweight `ModelInvocation` table with:

- role
- model
- prompt id + version
- target entity type/id
- input hash
- output hash
- status
- latency
- timeout
- fallback_used
- parse_valid
- created_at

Do not store full prompts blindly forever if privacy or size is a concern; store hashes and selectively sampled payloads.

### Prompt versioning

Every production prompt should have:

- stable id
- semantic version
- owner/module
- intended schema

### Fallback policy

Fallbacks should exist, but be explicit:

- persist `is_fallback=True`
- mark workflow as degraded where relevant
- allow dashboard/operator filtering for degraded AI outcomes

### Leader/worker orchestration

A stronger leader/worker layer is justified only in two places:

- agent/chat orchestration,
- multi-pass AI review flows where executor and reviewer meaningfully differ.

Do not create an internal agent swarm for ordinary deterministic pipeline steps.

## Config and Control Plane

### Split config into three classes

#### Deploy-time immutable config

- env vars
- database urls
- broker urls
- provider base urls
- security policy toggles that should not be changed by runtime API

#### Runtime policy

- reviewer enabled
- thresholds
- automation mode
- brand context
- pipeline policy
- outreach/reply behavior

Persist in DB, version it lightly, expose via admin API.

#### Secrets

- mail passwords
- provider tokens
- webhook secrets

Store behind a dedicated secret abstraction.

### Recommended policy split

Replace giant `OperationalSettings` with smaller policy aggregates:

- `AutomationPolicy`
- `BrandProfile`
- `PipelinePolicy`
- `OutreachPolicy`
- `ReplyPolicy`
- `NotificationPolicy`

## Frontend Target Architecture

### Goals

- One contract source.
- Server-first data loading for read-heavy screens.
- Smaller route components.
- Real cache/invalidation semantics.

### Recommended frontend shape

```text
dashboard/
  app/
    (routes as server components by default)
  features/
    leads/
      components/
      queries/
      actions/
      types.generated.ts
    outreach/
    inbox/
    pipeline/
  lib/
    api/
      generated/
      query-client.ts
```

### Contract strategy

Choose one:

- generated OpenAPI client + generated DTOs, or
- backend-exported schema package

Pragmatic recommendation:

- generate from OpenAPI in CI and commit the result initially.

### Data strategy

- Server Components for primary page composition.
- Client components only for:
  - chat streaming,
  - live polling widgets,
  - optimistic mutations,
  - map interactions,
  - rich tables/forms if needed.
- If client fetching remains significant, introduce TanStack Query.

## Observability Target

### Mandatory

- request id middleware
- correlation id propagation to Celery
- root workflow id
- structured event names for every workflow transition
- LLM invocation metrics
- provider call metrics

### Strongly recommended

- OpenTelemetry tracing for:
  - FastAPI
  - Celery
  - HTTPX
  - database
  - Ollama calls
- dashboards for:
  - workflow latency by step
  - fallback rate by prompt/model
  - retry counts
  - send failure rate
  - crawl yield rate

## Security Target

- Remove HTTP-based `.env` mutation.
- Use separate encryption key material for stored credentials.
- Add key versioning for secret rotation.
- Add outbound fetch guardrails:
  - SSRF allow/deny rules
  - timeouts
  - response size limits
  - content-type checks
- Restrict settings/control plane endpoints behind stronger auth than a single global API key if this leaves private local-only usage.

## Testing Target

### Pyramid for this repo

- Pure unit tests:
  - dedup policy
  - scoring rules
  - prompt builders
  - sanitizers
  - domain policies
- Integration tests on PostgreSQL:
  - repositories
  - transaction boundaries
  - Alembic migrations
  - async step execution
- Workflow tests:
  - pipeline transitions
  - retries
  - idempotency
  - degraded AI paths
- Contract tests:
  - OpenAPI -> generated TS drift
  - webhook payload compatibility
- Provider-adapter tests:
  - SMTP/IMAP/Kapso/Telegram/Ollama wrappers

### Pragmatic posture

You do not need a huge testing platform.
You do need real PostgreSQL and real migration coverage.

## What Should Stay Simple

- Keep one deployable app + one worker stack.
- Keep Celery + Redis instead of inventing an internal workflow engine.
- Keep FastAPI and Next.js.
- Keep the dashboard tightly coupled to the backend domain.
- Keep most read models in the monolith instead of creating a separate analytics service.

## What Must Become More Explicit

- workflow ownership
- transaction boundaries
- AI contracts
- settings classes
- frontend contracts
- observability lineage

## Primary Source Alignment

- SQLAlchemy transaction scoping and test transaction patterns:
  https://docs.sqlalchemy.org/en/21/orm/session_transaction.html
- Celery task idempotency/retry semantics:
  https://docs.celeryq.dev/en/v5.1.1/userguide/tasks.html
  https://docs.celeryq.dev/en/3.1/userguide/tasks.html
- Next.js App Router / Server Components:
  https://nextjs.org/docs/app
  https://nextjs.org/docs/14/app/building-your-application/rendering/server-components
- Ollama structured outputs:
  https://ollama.com/blog/structured-outputs
