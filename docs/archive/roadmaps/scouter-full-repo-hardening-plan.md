> **ARCHIVED:** This document has been superseded. See [plans/refactor-roadmap.md](../../plans/refactor-roadmap.md) for the current version.

# Scouter Full Repo Hardening Plan

**Date:** 2026-04-06 (v3 — after third full audit)
**Source:** [scouter-full-repo-deep-audit.md](../audits/scouter-full-repo-deep-audit.md)
**Current score:** 8.7/10 → **Target: 9.5/10**

---

## What Was Already Done (Previous Hardening Sessions)

- ✅ Private import coupling in ai_office.py fixed
- ✅ NoneType race in review_tasks.py fixed
- ✅ `_track_failure` extracted to shared `workers/_helpers.py`
- ✅ Dynamic Tailwind classes replaced with static maps
- ✅ SSE JSON.parse wrapped in try/catch
- ✅ usePageData stale closure fixed
- ✅ deps.py deleted, get_db imported directly
- ✅ Shared task-utils.ts and ModelBadge extracted
- ✅ Tool registry caches inspect.signature at registration
- ✅ Pipeline orphan detection in janitor
- ✅ Singleton CheckConstraint on OperationalSettings
- ✅ Tests migrated to PostgreSQL via testcontainers
- ✅ Alembic migration chain test
- ✅ 16 new tests added (315 → 325 total)

---

## Phase 0 — Critical Correctness Fixes (30 minutes)

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 0.1 | Replace `outcomes!.by_industry` with proper null check | HIGH | 5 min | `dashboard/components/performance/ai-score-panel.tsx:131` |
| 0.2 | Move whatsapp_actions rate limiting from in-memory dict to Redis | MEDIUM | 30 min | `app/services/comms/whatsapp_actions.py:39-49` |
| 0.3 | Add null guard in execute_generate_draft to prevent silent failure | MEDIUM | 5 min | `app/services/comms/whatsapp_actions.py:162-165` |
| 0.4 | Fix `DbSession = Annotated[object, ...]` to use `Session` | MEDIUM | 2 min | `app/api/v1/settings/operational.py:18` |

**Definition of Done:** All 4 items fixed, tests pass, no new regressions.

---

## Phase 1 — Remove AI Slop / Reduce Low-Signal Complexity (1-2 hours)

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 1.1 | Extract shared `_execute_draft_action(db, draft_id, target_status)` from approve/reject | MEDIUM | 15 min | `app/services/comms/whatsapp_actions.py` |
| 1.2 | Replace 10 bare `except Exception: pass` with `logger.debug(..., exc_info=True)` | MEDIUM | 30 min | `scoring/rules.py`, `celery_app.py`, `pipeline_tasks.py`, `research_tasks.py`, `whatsapp_actions.py`, `operational.py`, `telegram.py`, `territory_crawl.py` |
| 1.3 | Normalize structlog imports: replace 5 `structlog.get_logger()` with `app.core.logging.get_logger` | LOW | 10 min | `closer_service.py`, `context_service.py`, `outcome_analysis_service.py`, `outcome_tracking_service.py`, `auto_send_service.py` |
| 1.4 | Remove `except TypeError: pass` test-mock accommodation in scoring | LOW | 5 min | `app/scoring/rules.py:119` |
| 1.5 | Fix `return undefined as T` with proper overload or type guard | LOW | 10 min | `dashboard/lib/api/client.ts:74` |
| 1.6 | Fix redundant `"generated" \| string` union type | NIT | 2 min | `dashboard/types/index.ts:162` |

**Definition of Done:** All items fixed, `ruff check` clean, `npx tsc --noEmit` clean, tests pass.

---

## Phase 2 — Strengthen Contracts and Runtime Safety (1-2 days)

| # | Task | Effort | Files |
|---|------|--------|-------|
| 2.1 | Add pagination to dossiers page (backend endpoint + frontend infinite scroll) | 4 hrs | `app/api/v1/leads.py`, `dashboard/app/dossiers/page.tsx` |
| 2.2 | Add pagination to responses page | 2 hrs | `dashboard/app/responses/page.tsx` |
| 2.3 | Add backend geo endpoint for map page (lightweight lat/lng + name only) | 4 hrs | `app/api/v1/leads.py`, `dashboard/app/map/page.tsx` |
| 2.4 | Extract shared `NotificationListView` from security + notifications pages | 1-2 hrs | NEW: `dashboard/components/shared/notification-list-view.tsx` |
| 2.5 | Update README metric counts (file counts, test counts) | 10 min | `README.md` |

**Definition of Done:** All pages paginated/optimized, shared component extracted, README accurate, type check clean.

---

## Phase 3 — Improve Maintainability and Repo Ergonomics (2-3 hours)

| # | Task | Effort | Files |
|---|------|--------|-------|
| 3.1 | Migrate task_routes from backward-compat `app.workers.tasks.*` to direct module paths | 30 min | `app/workers/celery_app.py` |
| 3.2 | Add deprecation warning to `workers/tasks.py` re-exports | 10 min | `app/workers/tasks.py` |
| 3.3 | Archive older audit/roadmap docs (pre-April 4) to `docs/archive/` | 15 min | `docs/audits/`, `docs/roadmaps/` |
| 3.4 | Add `celerybeat-schedule` and `scouter.egg-info/` to .gitignore | 2 min | `.gitignore` |
| 3.5 | Bump batch review prompts from v1 to v2 for consistency | 5 min | `app/llm/prompt_registry.py` |

**Definition of Done:** All items done, no functional changes, repo cleaner.

---

## Phase 4 — Strengthen Tests and Verification (3-5 days)

| # | Task | Effort | Priority |
|---|------|--------|----------|
| 4.1 | Set up frontend testing infrastructure (vitest + testing-library) | 4 hrs | P0 |
| 4.2 | Add component tests for leads page, AI office, onboarding wizard | 2-3 days | P1 |
| 4.3 | Add Celery integration test (full pipeline chain with Redis testcontainer) | 1-2 days | P1 |
| 4.4 | Add tests for Telegram endpoints (webhook, send response) | 4 hrs | P2 |
| 4.5 | Add batch review end-to-end test | 1 day | P2 |
| 4.6 | Add tests for territory endpoints | 2 hrs | P3 |
| 4.7 | Add LLM invocation degradation rate metrics (Prometheus) | 4 hrs | P3 |

**Definition of Done:** Frontend tests running in CI, Celery integration test passing, all P1/P2 items complete.

---

## Commit Strategy

Follow conventional commits. One logical change per commit. Prefer many small commits over few large ones.

### Phase 0 commits (example)
```
fix(frontend): replace non-null assertion with null check in ai-score-panel
fix(whatsapp): move action rate limiting from memory to Redis
fix(whatsapp): add null guard in execute_generate_draft
fix(settings): use Session type for DbSession annotation
```

### Phase 1 commits (example)
```
refactor(whatsapp): extract shared draft action helper
fix(backend): replace bare except:pass with logger.debug across 10 files
refactor(logging): normalize structlog imports to app.core.logging
fix(scoring): remove test-mock TypeError accommodation
fix(frontend): fix type lie in apiFetch 204 handling
fix(types): remove redundant string union in ReplyAssistantDraft status
```

---

## PR Breakdown

| PR | Phases | Risk | Review Needed |
|----|--------|------|---------------|
| PR 1: Quick correctness fixes | Phase 0 | Low | Quick review |
| PR 2: Slop cleanup | Phase 1 | Low | Standard review |
| PR 3: Pagination and shared components | Phase 2 | Medium | Thorough review |
| PR 4: Repo ergonomics | Phase 3 | Low | Quick review |
| PR 5: Frontend testing setup | Phase 4.1-4.2 | Medium | Thorough review |
| PR 6: Celery integration tests | Phase 4.3 | Medium | Thorough review |
| PR 7: Remaining tests | Phase 4.4-4.7 | Low | Standard review |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Redis rate limiting changes WhatsApp action behavior | Test with existing WhatsApp flow before deploying |
| Pagination changes break existing frontend state | Add pagination params as optional with sensible defaults |
| Shared notification component breaks both pages | Extract carefully, test both routes |
| Frontend testing framework setup is heavyweight | Use vitest (already in Next.js ecosystem), minimal config |
| Celery integration tests are slow | Run in separate CI job, not blocking main test suite |

---

## Definition of Done by Phase

### Phase 0
- [ ] All 4 correctness fixes applied
- [ ] `pytest` passes
- [ ] `npx tsc --noEmit` passes
- [ ] No new regressions in affected areas

### Phase 1
- [ ] All 6 cleanup items complete
- [ ] `ruff check` clean
- [ ] `npx tsc --noEmit` clean
- [ ] `pytest` passes
- [ ] No behavior changes (refactor only)

### Phase 2
- [ ] All 5 items complete
- [ ] Paginated pages tested with 0, 10, 100+ records
- [ ] Shared notification component renders correctly on both pages
- [ ] README metrics verified against actual counts

### Phase 3
- [ ] All 5 ergonomic items complete
- [ ] No functional changes
- [ ] Old docs archived, not deleted

### Phase 4
- [ ] Frontend test suite running (vitest)
- [ ] At least 10 frontend component tests
- [ ] At least 1 Celery integration test (full pipeline chain)
- [ ] Telegram endpoint tests passing
- [ ] Overall test count: 350+ (currently 325)
- [ ] Audit score target: 9.5/10

---

## Score Projection

| Phase | Expected Score | Delta |
|-------|---------------|-------|
| Current | 8.7/10 | — |
| After Phase 0 | 8.9/10 | +0.2 |
| After Phase 1 | 9.0/10 | +0.1 |
| After Phase 2 | 9.2/10 | +0.2 |
| After Phase 3 | 9.3/10 | +0.1 |
| After Phase 4 | 9.5/10 | +0.2 |
