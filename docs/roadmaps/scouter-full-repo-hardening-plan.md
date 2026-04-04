# Scouter Full Repo Hardening Plan

**Date:** 2026-04-04
**Source:** [scouter-full-repo-deep-audit.md](../audits/scouter-full-repo-deep-audit.md)
**Goal:** Raise repo from 7.5/10 to 9/10 through targeted, incremental fixes

---

## Phase 0 — Critical Correctness Fixes

**Timeline:** 1 day
**Goal:** Fix bugs that are actively broken or producing wrong results

| # | Task | Finding | Effort | Files |
|---|------|---------|--------|-------|
| 0.1 | Replace dynamic Tailwind classes with lookup maps | F1 | 30 min | `app/ai-office/page.tsx`, `components/leads/ai-decisions-panel.tsx`, `components/dashboard/ai-health-card.tsx` |
| 0.2 | Add `runtime_mode` + `pricing_matrix` to `OperationalSettingsResponse` | M1 | 10 min | `app/schemas/operational_settings.py` |
| 0.3 | Fix `is_suppressed` to use `sqlalchemy.or_()` instead of AND | B3 | 5 min | `app/services/leads/lead_service.py` |
| 0.4 | Wrap SSE JSON.parse in try/catch | F9 | 5 min | `dashboard/lib/hooks/use-chat.ts` |
| 0.5 | Fix `usePageData` stale closure (add `fetcher` to deps or use ref) | F5 | 30 min | `dashboard/lib/hooks/use-page-data.ts` |
| 0.6 | Fix trailing slash in briefs router | B8 | 2 min | `app/api/v1/briefs.py` |
| 0.7 | Fix `formatRelativeTime` for negative/future dates | F20 | 2 min | `dashboard/lib/formatters.ts` |
| 0.8 | Add `api_key` to log scrubber sensitive key regex | B16 | 2 min | `app/core/logging.py` |
| 0.9 | Read model names from config in AI office status endpoint | B4 | 15 min | `app/api/v1/ai_office.py` |

**Commit strategy:**
```
fix(frontend): replace dynamic Tailwind classes with static lookup maps
fix(schemas): add runtime_mode and pricing_matrix to OperationalSettingsResponse
fix(leads): use OR logic in suppression check
fix(chat): wrap SSE JSON parse in try/catch
fix(hooks): fix stale closure in usePageData
fix(briefs): remove trailing slash inconsistency
fix(frontend): handle future dates in formatRelativeTime
fix(logging): add api_key to sensitive key scrubber
fix(ai-office): read model names from config instead of hardcoding
```

**Verification:** `pytest -q` passes, `npx tsc --noEmit` clean, manual check that AI office page renders colors correctly.

---

## Phase 1 — Remove AI Slop / Reduce Low-Signal Complexity

**Timeline:** 1-2 days
**Goal:** Eliminate copy-paste debt, remove trivial wrappers, consolidate duplicated logic

| # | Task | Finding | Effort | Files |
|---|------|---------|--------|-------|
| 1.1 | Extract shared `NotificationListView` from security + notifications pages | F3 | 1 hour | `app/security/page.tsx`, `app/notifications/page.tsx`, NEW: `components/shared/notification-list-view.tsx` |
| 1.2 | Extract `STEP_CONFIG`, helpers, `ModelBadge` to shared modules | F4 | 30 min | `components/layout/activity-pulse.tsx`, `app/activity/page.tsx`, NEW: `lib/task-utils.ts`, `components/shared/model-badge.tsx` |
| 1.3 | Delete `app/api/deps.py`, import `get_db` directly | B12 | 10 min | `app/api/deps.py`, all routers importing `get_session` |
| 1.4 | Move `TelegramCredentials` type to `types/index.ts` | F13 | 10 min | `dashboard/lib/api/client.ts`, `dashboard/types/index.ts` |
| 1.5 | Fix `WhatsAppCredentials` import to use canonical location | F14 | 5 min | `dashboard/app/settings/page.tsx` |
| 1.6 | Remove double `LayoutShell` nesting in dossiers + briefs pages | F15 | 15 min | `app/dossiers/page.tsx`, `app/briefs/page.tsx` |
| 1.7 | Remove unused `StepIcon` variable in ActiveTaskCard | F16 | 2 min | `app/activity/page.tsx` |
| 1.8 | Remove phantom frontend fields (`owner`, `notes`, `business_name`) | M2, M3 | 5 min | `dashboard/types/index.ts` |
| 1.9 | Remove `_call_ollama_chat` from `__all__` exports | NIT | 2 min | `app/llm/client.py` |
| 1.10 | Replace `console.error` with `sileo.error()` in map page | F18 | 5 min | `app/map/page.tsx` |
| 1.11 | Document or compute velocity multipliers in performance page | F21 | 15 min | `app/performance/page.tsx` |
| 1.12 | Remove or clarify "placeholder" comment in AI Health Card | F17 | 5 min | `components/dashboard/ai-health-card.tsx` |

**Commit strategy:**
```
refactor(frontend): extract NotificationListView from security and notifications pages
refactor(frontend): extract task step config and ModelBadge to shared modules
chore(api): remove trivial deps.py wrapper, import get_db directly
refactor(types): consolidate TelegramCredentials and WhatsAppCredentials in types/index.ts
fix(frontend): remove double LayoutShell nesting in dossiers and briefs
chore(frontend): clean unused variables and phantom type fields
chore(llm): clean __all__ exports in client.py
fix(frontend): use toast instead of console.error in map page
docs(frontend): document velocity multiplier derivation
```

**Verification:** `pytest -q` passes, `npx tsc --noEmit` clean, grep for removed imports returns 0 matches.

---

## Phase 2 — Strengthen Contracts and Runtime Safety

**Timeline:** 2-3 days
**Goal:** Fix runtime risks that could cause failures under real load

| # | Task | Finding | Effort | Files |
|---|------|---------|--------|-------|
| 2.1 | Rewrite channel router to avoid creating thread pool per message | B1 | 1-2 days | `app/agent/channel_router.py` |
| 2.2 | Add cross-channel conversation isolation (filter by channel_id) | B5 | 2 hours | `app/agent/channel_router.py` |
| 2.3 | Cache `inspect.signature` check in ToolDefinition at registration | B10 | 30 min | `app/agent/tool_registry.py`, `app/agent/core.py` |
| 2.4 | Add `db` parameter option to `_persist_invocation` | B6 | 30 min | `app/llm/client.py` |
| 2.5 | Replace module-level rate limit global with Redis-based limiter | B7 | 1 hour | `app/api/v1/setup.py` |
| 2.6 | Add pipeline orphan detection (check for stuck "running" pipelines) | B9 | 2 hours | `app/workers/janitor.py` or NEW: `app/workers/pipeline_health.py` |
| 2.7 | Replace `getLeadsWithCoords` unbounded loop with backend geo endpoint | F2 | 1 day | NEW: `app/api/v1/leads.py` endpoint, `dashboard/lib/api/client.ts`, `dashboard/app/map/page.tsx` |
| 2.8 | Add pagination to leads page | F7 | 1 day | `dashboard/app/leads/page.tsx`, NEW: pagination component |
| 2.9 | Create lightweight `/leads/names` endpoint for name resolution | F6 | 2 hours | `app/api/v1/leads.py`, `dashboard/lib/api/client.ts`, update 5 pages |
| 2.10 | Add `CheckConstraint('id = 1')` to OperationalSettings | B15 | 15 min | `app/models/settings.py`, new migration |
| 2.11 | Use streaming export with `.yield_per(100)` | B13 | 30 min | `app/api/v1/leads.py` |
| 2.12 | Add `Query(ge=1, le=500)` constraint on briefs limit | B14 | 5 min | `app/api/v1/briefs.py` |
| 2.13 | Cache readiness result in ReadinessGate | F8 | 30 min | `dashboard/components/layout/readiness-gate.tsx` |
| 2.14 | Replace `stats!` non-null assertion with null guard | F10 | 5 min | `dashboard/app/panel/page.tsx` |
| 2.15 | Replace `as any` with proper typing in map updateTerritory | F11 | 10 min | `dashboard/app/map/page.tsx` |
| 2.16 | Replace `Record<string, any>` with `Record<string, unknown>` | F12 | 10 min | `dashboard/types/index.ts`, `app/performance/page.tsx`, `app/notifications/page.tsx` |
| 2.17 | Upgrade crypto key derivation to PBKDF2HMAC | B2 | 1 day | `app/core/crypto.py`, migration for re-encrypting existing values |
| 2.18 | Add warning log on `decrypt_safe` InvalidToken | B11 | 5 min | `app/core/crypto.py` |

**Commit strategy:** One commit per logical change. Backend and frontend changes separated. Migration commits separate from code commits.

**Verification:** `pytest -q` passes, `npx tsc --noEmit` clean, load test channel router with concurrent messages, verify pipeline orphan detection in janitor logs.

---

## Phase 3 — Improve Maintainability and Repo Ergonomics

**Timeline:** 2-3 days
**Goal:** Reduce cost of future changes, improve developer experience

| # | Task | Finding | Effort | Files |
|---|------|---------|--------|-------|
| 3.1 | Replace hardcoded README metrics with CI-generated badge or script | D3 | 1 hour | `README.md`, `scripts/` |
| 3.2 | Update `docs/architecture/audit.md` post-Agent OS with current state | D1 | 2 hours | `docs/architecture/audit.md` |
| 3.3 | Write top 3 ADRs from the recommended 10 | D2 | 1-2 days | NEW: `docs/architecture/adrs/` |
| 3.4 | Add `loading.tsx` files for heavy pages (leads, performance, panel, activity) | F22 | 2 hours | NEW: 4 `loading.tsx` files |
| 3.5 | Reduce silent error swallowing — add console.warn to page-level catches | F19 | 1 hour | ~10 page files |
| 3.6 | Extract test data seeding helpers to shared conftest fixtures | T6 | 1 hour | `tests/conftest.py`, `tests/test_api_inbound_mail.py`, `tests/test_api_inbound_classification.py` |
| 3.7 | Update security-backlog.md with current resolution status | D1 | 30 min | `docs/operations/security-backlog.md` |
| 3.8 | Add `.editorconfig` for consistent formatting across editors | NIT | 10 min | NEW: `.editorconfig` |

**Commit strategy:**
```
docs(readme): replace hardcoded metrics with generated values
docs(architecture): update audit.md to reflect post-Agent OS state
docs(adrs): write ADR-001 through ADR-003
feat(frontend): add loading.tsx for heavy pages
fix(frontend): add error logging to page-level catch blocks
refactor(tests): extract shared data seeding to conftest fixtures
docs(security): update backlog with current resolution status
chore(repo): add .editorconfig
```

---

## Phase 4 — Strengthen Tests and Verification

**Timeline:** 5-7 days (can be parallelized)
**Goal:** Close the major test gaps that undermine confidence

| # | Task | Finding | Effort | Priority |
|---|------|---------|--------|----------|
| 4.1 | Migrate test suite to PostgreSQL via Docker fixture | T1 | 2-3 days | **P0** — this is the single highest-impact change for confidence |
| 4.2 | Add Alembic migration chain test | T2 | 1-2 days | **P0** — verifies migrations apply cleanly on Postgres |
| 4.3 | Add Celery integration tests (at least for full pipeline chain) | T4 | 1-2 days | **P1** — verifies task serialization, routing, retry |
| 4.4 | Add frontend component tests for critical pages | T5 | 2-3 days | **P1** — at minimum: leads page, AI office, onboarding |
| 4.5 | Replace WhatsApp schema introspection tests with behavioral tests | T7 | 2 hours | **P2** |
| 4.6 | Add pipeline end-to-end test (mock LLM, real DB, real task dispatch) | — | 1 day | **P1** |

### 4.1 Detail: PostgreSQL Test Migration

```python
# conftest.py approach
import docker
import sqlalchemy

@pytest.fixture(scope="session")
def postgres_container():
    client = docker.from_env()
    container = client.containers.run(
        "postgres:16-alpine",
        environment={"POSTGRES_PASSWORD": "test", "POSTGRES_DB": "scouter_test"},
        ports={"5432/tcp": None},
        detach=True,
    )
    # wait for ready
    yield container
    container.stop()
    container.remove()

@pytest.fixture(scope="session")
def engine(postgres_container):
    port = postgres_container.ports["5432/tcp"][0]["HostPort"]
    return create_engine(f"postgresql://postgres:test@localhost:{port}/scouter_test")
```

### 4.2 Detail: Migration Chain Test

```python
def test_migration_chain(postgres_engine):
    """Verify all 37 migrations apply cleanly to fresh Postgres."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(postgres_engine.url))
    command.upgrade(alembic_cfg, "head")
    # verify final state matches models
    inspector = inspect(postgres_engine)
    assert set(inspector.get_table_names()) >= {"leads", "pipeline_runs", ...}
```

**Commit strategy:** One PR per test category. Migration to Postgres is its own PR (largest, most impactful).

---

## Commit Strategy

All changes follow conventional commits as defined in AGENTS.md:
- `fix(scope):` for correctness fixes
- `refactor(scope):` for structural improvements
- `test(scope):` for test additions
- `docs(scope):` for documentation updates
- `chore(scope):` for cleanup and repo hygiene
- `feat(scope):` for new endpoints or capabilities

One logical change per commit. Backend and frontend changes in separate commits. Migration commits separate from code commits.

---

## PR Breakdown

| PR | Phase | Title | Size |
|----|-------|-------|------|
| PR 1 | Phase 0 | fix: critical correctness fixes (9 items) | Small |
| PR 2 | Phase 1 | refactor: remove AI slop and consolidate duplicates | Medium |
| PR 3 | Phase 2a | fix: runtime safety — channel router, pipeline health, crypto | Medium |
| PR 4 | Phase 2b | feat: leads pagination, geo endpoint, name resolution | Medium |
| PR 5 | Phase 2c | fix: frontend contract and type safety improvements | Small |
| PR 6 | Phase 3 | docs + maintainability improvements | Small |
| PR 7 | Phase 4a | test: migrate test suite to PostgreSQL | Large |
| PR 8 | Phase 4b | test: add Alembic migration + Celery integration tests | Medium |
| PR 9 | Phase 4c | test: add frontend component tests | Medium |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Postgres test migration breaks CI | Run SQLite and Postgres in parallel during transition |
| Crypto key migration corrupts encrypted values | Write reversible migration with backup before re-encryption |
| Channel router rewrite changes agent behavior | Add integration test before and after rewrite to verify behavior parity |
| Frontend refactor breaks pages | Add TypeScript compilation check in CI + smoke test critical paths |
| Phase 4 scope creep | Timebox each test category. P0 first, P2 only if time permits |

---

## Definition of Done by Phase

### Phase 0 ✓ when:
- All 9 fixes committed
- `pytest -q` passes (299+ tests)
- `npx tsc --noEmit` clean
- AI office page renders with correct colors (manual verify)

### Phase 1 ✓ when:
- Security + notifications share a single component
- Activity step config exists in one place only
- `deps.py` deleted
- No phantom type fields in `types/index.ts`
- `grep -r "deps" dashboard/ app/api/` returns 0 matches for old import

### Phase 2 ✓ when:
- Channel router creates 0 new threads per message
- Pipeline orphan detection runs on janitor sweep
- Map page uses backend geo endpoint (no unbounded loop)
- Leads page has pagination controls
- Crypto uses PBKDF2HMAC
- All `as any` and `Record<string, any>` removed from frontend

### Phase 3 ✓ when:
- README metrics match `wc -l` / `pytest --collect-only` output
- audit.md updated with post-Agent OS state
- 3+ ADRs written
- Heavy pages have `loading.tsx`
- security-backlog.md up to date

### Phase 4 ✓ when:
- Test suite runs against PostgreSQL (not SQLite)
- Migration chain test passes on fresh Postgres
- At least one Celery integration test verifies full pipeline dispatch
- At least 3 frontend component tests exist
- Test count ≥ 310 (current 299 + new tests)
- CI runs all test categories on every PR
