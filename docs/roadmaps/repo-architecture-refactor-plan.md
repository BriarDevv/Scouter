# Scouter Repository Architecture Refactor Plan

**Date:** 2026-04-06
**Source:** [repo-architecture-deep-audit.md](../audits/repo-architecture-deep-audit.md)
**Current score:** 7.5 / 10
**Target score:** 9.0 / 10
**Approach:** Incremental — no big-bang rewrites, no breaking changes

---

## Guiding Principles

1. **One change at a time.** Each phase is independently valuable and shippable.
2. **Tests first.** Every structural change must be validated by existing tests passing.
3. **No framework migrations.** Keep FastAPI, Celery, Next.js, SQLAlchemy, Tailwind.
4. **Optimize for the solo maintainer.** Don't build for a 10-person team.
5. **Backend before frontend.** Backend boundaries must be solid before generating frontend contracts.

---

## Phase 1: Structural Cleanup (Score: 7.5 -> 8.0)

**Goal:** Fix naming, file placement, and obvious structural smells.
**Risk:** Zero — no behavior changes.
**Time:** 1-2 sessions.

### 1.0 Fix broken `.claude/commands/` paths (URGENT)

4 command files contain stale `/home/mateo` paths (7 occurrences). These commands fail when invoked:
- `preflight.md:5` — `cd /home/mateo/src/Scouter`
- `stack.md:8,11,14` — `cd /home/mateo/src/Scouter`
- `test.md:7,10` — `cd /home/mateo/src/Scouter`
- `agent-os.md:37` — `cd /home/mateo/Scouter` (also wrong structure)

Also fix `test.md:6` which says "SQLite" — tests use PostgreSQL via testcontainers.

### 1.1 Rename `dashboard_svc` -> `dashboard`

```
app/services/dashboard_svc/ -> app/services/dashboard/
```

Update all imports. Run `ruff check` and `pytest`.

### 1.2 Merge `app/outreach/` into `app/services/outreach/`

Move `app/outreach/generator.py` into `app/services/outreach/generator.py`.
Update all imports. Delete empty `app/outreach/` package.

### 1.3 Move misplaced root services

| File | Move to |
| --- | --- |
| `app/services/instagram_scraper.py` | `app/crawlers/instagram_scraper.py` |
| `app/services/setup_service.py` | `app/services/settings/setup_service.py` |

Update imports. Both are clear domain misplacements.

### 1.4 Move misplaced frontend components

| File | Move to |
| --- | --- |
| `components/shared/reply-draft-panel.tsx` | `components/leads/reply-draft-panel.tsx` |
| `components/shared/notification-list-view.tsx` | `components/notifications/notification-list-view.tsx` (new folder) |

Update imports. These are feature components, not shared primitives.

### 1.5 Add missing loading states

Add `loading.tsx` to the 12 pages that lack one:
`ai-office`, `briefs`, `dossiers`, `map`, `notifications`, `onboarding`, `outreach`, `responses`, `security`, `settings`, `suppression`, `leads/[id]`.

Use a consistent skeleton pattern matching existing loading files.

### 1.6 Delete dead files (after verification)

- Verify `scripts/migrate-legacy-stack.sh` is unused, delete if confirmed.
- Verify `scouter.egg-info/` is gitignored (it is) — no action needed.

### Validation

- `pytest -v` passes
- `ruff check app/` clean
- `cd dashboard && npx tsc --noEmit` clean
- No import errors

---

## Phase 2: Frontend Architecture (Score: 8.0 -> 8.5)

**Goal:** Split monolithic frontend files, improve per-page resilience.
**Risk:** Low — refactoring existing code, no behavior changes.
**Time:** 2-3 sessions.

### 2.1 Split `types/index.ts` (982 LOC)

Split into domain-specific type files:

```
dashboard/types/
  index.ts          # Re-exports for backwards compatibility
  leads.ts          # Lead, LeadStatus, LeadName, etc.
  outreach.ts       # OutreachDraft, OutreachDelivery, DraftStatus, etc.
  pipeline.ts       # PipelineRunSummary, TaskResponse, etc.
  settings.ts       # OperationalSettings, LLMSettings, MailSettings, etc.
  dashboard.ts      # DashboardStats, PipelineStage, etc.
  mail.ts           # EmailThreadDetail, InboundMessage, etc.
  notifications.ts  # NotificationItem, NotificationCounts, etc.
  chat.ts           # ChatConversation, ChatMessage, etc.
  research.ts       # LeadResearchReport, CommercialBrief, etc.
  common.ts         # PaginatedResponse, TimeSeriesPoint, etc.
```

Keep `index.ts` as a barrel re-export so existing imports don't break.

### 2.2 Split `lib/api/client.ts` (884 LOC)

Split into domain-specific API modules:

```
dashboard/lib/api/
  client.ts         # apiFetch() base + re-exports
  leads.ts          # fetchLeads, fetchLead, etc.
  outreach.ts       # fetchDrafts, approveDraft, etc.
  pipeline.ts       # startPipeline, fetchPipelineRuns, etc.
  settings.ts       # fetchSettings, updateSettings, etc.
  dashboard.ts      # fetchDashboardStats, etc.
  mail.ts           # fetchInboundMessages, etc.
  notifications.ts  # fetchNotifications, etc.
  chat.ts           # fetchConversations, etc.
  research.ts       # fetchResearchReport, etc.
```

Keep `client.ts` exporting `apiFetch` and re-exporting all domain functions.

### 2.3 Add per-page error boundaries

Add `error.tsx` to each route folder. Use a consistent pattern:

```tsx
"use client";
export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (/* consistent error UI */);
}
```

### 2.4 Split `app/llm/prompts.py` (714 LOC)

```
app/llm/prompts/
  __init__.py       # Re-exports
  lead.py           # Lead analysis/quality prompts
  outreach.py       # Draft generation prompts
  reply.py          # Reply/closer prompts
  research.py       # Research/brief prompts
  review.py         # Reviewer prompts
  system.py         # System/agent prompts
```

### Validation

- `cd dashboard && npx tsc --noEmit` clean
- `pytest -v` passes (backend prompt split)
- All frontend pages render correctly
- No broken imports

---

## Phase 3: Service Boundary Hardening (Score: 8.5 -> 9.0)

**Goal:** Reduce cross-service coupling and establish explicit public APIs.
**Risk:** Medium — changes internal service interfaces.
**Time:** 3-5 sessions.

### 3.1 Explicit `__init__.py` exports for each service sub-package

Each service sub-package should define its public API in `__init__.py`:

```python
# app/services/outreach/__init__.py
from app.services.outreach.outreach_service import create_draft, list_drafts, update_draft
from app.services.outreach.auto_send_service import run_auto_send
from app.services.outreach.mail_service import send_draft
```

This makes it clear what each sub-package exposes and what's internal.

### 3.2 Extract notification dispatch from business services

Currently: `scoring_service.py` calls `notification_emitter.on_high_score_lead()` inline.

Target: Services return events/results. Callers (workers/workflows) decide to emit notifications.

```python
# Before (in scoring_service.py)
def score_lead(db, lead_id):
    ...
    from app.services.notifications.notification_emitter import on_high_score_lead
    on_high_score_lead(db, lead)

# After
def score_lead(db, lead_id) -> ScoringResult:
    ...
    return ScoringResult(lead=lead, is_high_score=True)

# In worker/workflow
result = score_lead(db, lead_id)
if result.is_high_score:
    on_high_score_lead(db, result.lead)
```

Apply this pattern to all notification dispatch sites (~8 locations).

### 3.3 Reduce `operational_settings_service` as universal import

Currently imported by: batch_review, inbox (3 files), notifications, outreach, research.

Options:
1. **Settings injection** — pass effective settings as a parameter to service functions instead of importing and fetching inside.
2. **Settings context** — create a `SettingsContext` dataclass passed down through workflows.

Prefer option 2 for workflows — compute settings once at workflow start, pass through.

### 3.4 Extract `ai_office.py` god router into a service

`app/api/v1/ai_office.py` (423 LOC) contains 15+ raw SQLAlchemy queries, 8 model imports, and inline Pydantic models. Create `app/services/dashboard/ai_office_service.py` and move all query logic there. Move inline schemas to `app/schemas/ai_office.py`. The router should become ~80 LOC of pure delegation.

### 3.5 Fix `core/config.py` -> `llm/catalog.py` upward dependency

`app/core/config.py` imports `app.llm.catalog` at module level. Move `DEFAULT_ROLE_MODEL_MAP` and `DEFAULT_SUPPORTED_MODELS` into `app/core/defaults.py` or accept them as string defaults in Settings. This breaks the `core/` -> `llm/` dependency that causes LLM module loading at config time.

### 3.6 Fix model-layer violation

Move `LLMInvocationStatus` from `app/llm/types.py` to `app/models/enums.py` or define it in-model.
`app/models/llm_invocation.py` should not import from `app/llm/`.

### 3.7 Fix schema-model coupling

Schemas import model enums (11 imports). Extract shared enums into `app/schemas/enums.py` or `app/core/enums.py` that both models and schemas import from.

### Validation

- `pytest -v` passes
- `ruff check app/` clean
- No circular import errors
- Cross-service import count reduced from 40+ to <20

---

## Phase 4: Transaction Boundary Discipline (Score: 9.0 -> 9.2)

**Goal:** Move `db.commit()` ownership to workflow coordinators.
**Risk:** Medium-High — changes persistence timing.
**Time:** 3-5 sessions, must be done incrementally.

### 4.1 Identify commit-free service functions

Many service functions already don't commit — they mutate and return. Catalog which ones do and don't.

### 4.2 Push commits from services to callers

For each service that calls `db.commit()`:
1. Remove the `commit()`.
2. Have the calling worker/workflow/API handle the commit.
3. Test that the behavior is identical.

**Do this one service sub-package at a time.** Start with the smallest (`scoring/`, `research/`), then `leads/`, then `outreach/`, then `inbox/`.

### 4.3 Add workflow transaction coordinators

For complex workflows (batch pipeline, lead pipeline):

```python
def run_enrichment_step(db: Session, lead_id: UUID):
    """Enriches and scores a lead in a single transaction."""
    enrich_lead(db, lead_id)      # mutates, no commit
    score_lead(db, lead_id)       # mutates, no commit
    db.commit()                   # single commit point
```

### Validation

- `pytest -v` passes after each sub-package migration
- `db.commit()` count in services reduced from 98 to <20
- Workers/workflows own commit boundaries

---

## Phase 5: Observability and CI (Score: 9.2 -> 9.5+)

**Goal:** Add structural observability and enforce quality in CI.
**Risk:** Low — additive only.
**Time:** 2-3 sessions.

### 5.1 Add CI pipeline

Create `.github/workflows/ci.yml`:

```yaml
on: [push, pull_request]
jobs:
  backend:
    steps:
      - ruff check app/ tests/
      - pytest -v
  frontend:
    steps:
      - cd dashboard && npm ci
      - npx tsc --noEmit
      - npx vitest run
```

### 5.2 Add architecture guardrail tests

Extend `tests/test_arch_guardrails.py`:

```python
def test_no_commit_in_services():
    """Services should not call db.commit() directly."""
    # Scan services/ for .commit() calls

def test_no_model_imports_from_llm():
    """Models should not import from app.llm."""
    # Scan models/ for llm imports

def test_service_packages_have_init_exports():
    """Each service sub-package should define its public API."""
    # Check __init__.py files exist and have exports
```

### 5.3 Request correlation middleware

The `RequestContextMiddleware` already exists. Extend it to:
1. Propagate correlation ID to Celery task headers.
2. Include correlation ID in structlog context for all workers.

### 5.4 LLM invocation metrics

Add Prometheus counters for:
- `llm_invocations_total` (role, model, status)
- `llm_invocation_latency_seconds` (role, model)
- `llm_fallback_total` (role, model)

### Validation

- CI pipeline runs and passes
- Architecture guardrail tests pass
- Correlation IDs visible in worker logs
- Prometheus `/metrics` shows LLM counters

---

## Future Considerations (Score: 9.5 -> 10.0)

These are **not planned** but would be needed for a true 10/10:

| Item | Impact | Complexity |
| --- | --- | --- |
| OpenAPI -> TypeScript contract generation | Eliminates manual type drift | Medium |
| Server component migration for read-heavy pages | Better performance, smaller bundles | High |
| TanStack Query for client data fetching | Cache, invalidation, optimistic updates | Medium |
| OpenTelemetry distributed tracing | Full request-to-LLM observability | High |
| Split `OperationalSettings` into policy aggregates | Cleaner config ownership | Medium |
| Split `LeadStatus` into lifecycle + pipeline stage | Correct domain modeling | Medium |

---

## Priority Matrix

| Phase | Impact | Risk | Effort | Priority |
| --- | --- | --- | --- | --- |
| Phase 1: Structural Cleanup | Medium | Zero | Low | **Do first** |
| Phase 2: Frontend Architecture | High | Low | Medium | **Do second** |
| Phase 3: Service Boundaries | High | Medium | Medium | **Do third** |
| Phase 4: Transaction Discipline | Very High | Medium-High | High | **Do fourth** |
| Phase 5: Observability + CI | Medium | Low | Medium | **Do fifth** |

---

## Score Progression

| After Phase | Projected Score | Key Improvement |
| --- | ---: | --- |
| Current | 7.5 | — |
| Phase 1 | 8.0 | Clean naming, file placement, loading states |
| Phase 2 | 8.5 | Split monolithic frontend files, prompt organization |
| Phase 3 | 9.0 | Explicit service boundaries, reduced coupling |
| Phase 4 | 9.2 | Transaction ownership, commit discipline |
| Phase 5 | 9.5 | CI enforcement, observability, guardrails |

---

## Tracking

Each phase should be committed with conventional commits:

```
refactor(services): rename dashboard_svc to dashboard
refactor(outreach): merge app/outreach into services/outreach
refactor(frontend): split types/index.ts into domain modules
refactor(frontend): split api/client.ts into domain modules
refactor(services): add explicit __init__.py exports
refactor(pipeline): push db.commit from services to workflow coordinators
ci(repo): add GitHub Actions CI pipeline
test(arch): add service boundary guardrail tests
```
