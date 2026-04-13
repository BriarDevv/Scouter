> **ARCHIVED:** This document has been superseded. See [plans/refactor-roadmap.md](../../plans/refactor-roadmap.md) for the current version.

# Scouter Repository Hardening Plan

**Date:** 2026-04-07
**Based on:** [repo-deep-audit.md](../audits/repo-deep-audit.md)
**Goal:** 6.5 -> 9.0/10

---

## Phase 0: Critical Fixes (1 day)

**Target: Eliminate live bugs and security vulnerabilities.**

| # | Task | File(s) | Effort | Impact |
|---|------|---------|--------|--------|
| 0.1 | Fix path traversal in storage service | `services/research/storage_service.py` | 15 min | CRITICAL |
| 0.2 | Fix variable shadowing in Google Maps crawler (`location` -> `coords`) | `crawlers/google_maps_crawler.py:138` | 5 min | CRITICAL |
| 0.3 | Add `db.commit()` to `patch_mail_credentials` | `api/v1/settings/credentials.py:43` | 5 min | CRITICAL |
| 0.4 | Fix history truncation (DESC LIMIT 50, then reverse) | `agent/core.py:134-141` | 15 min | CRITICAL |
| 0.5 | Add fallback factory to `classify_inbound_reply` | `llm/invocations/reply.py:49-57` | 15 min | HIGH |
| 0.6 | Scope LLM retry to transient errors only | `llm/client.py:319-323` | 15 min | HIGH |

**Validation:** Run `pytest -x -q`. All 337 tests must pass. Manually verify storage_service path guard with `../../` input.

---

## Phase 1: Agent Security Hardening (1-2 days)

**Target: Close the sanitization gap between Executor/Reviewer pipeline and Mote agent layer.**

| # | Task | File(s) | Effort | Impact |
|---|------|---------|--------|--------|
| 1.1 | Apply `sanitize_data_block` to tool result content in `format_tool_result` | `agent/hermes_format.py:97-122` | 1 hr | CRITICAL |
| 1.2 | Add anti-injection preamble variant to Mote's system prompt | `agent/prompts.py:14-18` | 30 min | HIGH |
| 1.3 | Fix tool call regex for nested JSON (greedy match or bracket-balancing) | `agent/hermes_format.py:43-46` | 2 hr | HIGH |
| 1.4 | Implement token budget estimation, trim oldest history preserving system prompt | `agent/core.py:278-284` | 4 hr | HIGH |
| 1.5 | Escape SQL wildcards (`%`, `_`) in `get_lead_detail` ilike | `agent/tools/leads.py:91` | 15 min | MEDIUM |
| 1.6 | Push `search_leads` filters into DB query | `agent/tools/leads.py:43-58` | 1 hr | MEDIUM |
| 1.7 | Fix SSRF DNS rebinding: pin resolved IP for fetch | `agent/scout_tools.py:46-74` | 1 hr | MEDIUM |

**Validation:** Add test in `test_security.py` for tool result injection. Add test for nested JSON tool call parsing. Run full suite.

---

## Phase 2: Data Integrity & Performance (2-3 days)

**Target: Fix transaction discipline, add missing indexes, eliminate memory-hungry queries.**

### 2A: Transaction Discipline

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 2A.1 | Convert 19 service-layer `db.commit()` to `db.flush()` | See M-1 file list in audit | 2 hr |
| 2A.2 | Remove `db.commit()` from agent tool handlers, centralize in agent loop | See M-2 file list in audit | 1 hr |
| 2A.3 | Add arch guardrail test: `test_services_do_not_call_db_commit` | `tests/test_arch_guardrails.py` | 30 min |

### 2B: Missing Indexes

| # | Task | Migration |
|---|------|-----------|
| 2B.1 | Add index on `lead_signals.lead_id` | New migration |
| 2B.2 | Add index on `artifacts.lead_id` | Same migration |
| 2B.3 | Add index on `commercial_briefs.research_report_id` | Same migration |

### 2C: Memory-Hungry Queries

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 2C.1 | Replace `_load_leads` with SQL aggregations (COUNT, AVG, GROUP BY) | `services/dashboard/dashboard_service.py` | 4 hr |
| 2C.2 | Push `outcome_analysis_service` aggregations to SQL | `services/pipeline/outcome_analysis_service.py` | 3 hr |
| 2C.3 | Add SQL LIMIT to territory leads query | `api/v1/territories.py:80-81` | 15 min |
| 2C.4 | Add `joinedload` to batch_reviews list and chat detail | `api/v1/batch_reviews.py:22`, `api/v1/chat.py:65` | 30 min |

### 2D: Connection Management

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 2D.1 | Replace Redis connection-per-call with module-level pool | `services/pipeline/operational_task_service.py` | 1 hr |
| 2D.2 | Cache Fernet key derivation at module load | `core/crypto.py` | 15 min |

**Validation:** Run full test suite. Add a test that verifies `lead_signals.lead_id` index exists. Benchmark dashboard stats endpoint before/after.

---

## Phase 3: API Hardening (2-3 days)

**Target: Add response models, rate limiting, and close test coverage gaps.**

### 3A: Response Models

| # | Task | Endpoints | Effort |
|---|------|-----------|--------|
| 3A.1 | Create Pydantic schemas for ai_office endpoints | 5 endpoints in `ai_office.py` | 1 hr |
| 3A.2 | Create Pydantic schemas for performance endpoints | 6 endpoints in `performance.py` | 1 hr |
| 3A.3 | Create Pydantic schemas for batch_reviews endpoints | 4 endpoints in `batch_reviews.py` | 1 hr |
| 3A.4 | Create Pydantic schemas for scoring/pipeline status endpoints | 6 endpoints | 1 hr |
| 3A.5 | Add `response_model=` to all 20 untyped endpoints | Various | 30 min |

### 3B: Rate Limiting

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 3B.1 | Wire `API_RATE_LIMIT` setting with `slowapi` middleware | `main.py`, `api/v1/enrichment.py`, `scoring.py`, `outreach.py`, `reviews.py` | 2 hr |

### 3C: Test Coverage

| # | Task | Test File | Effort |
|---|------|-----------|--------|
| 3C.1 | Add tests for territories API (6 endpoints) | `tests/test_api_territories.py` | 2 hr |
| 3C.2 | Add tests for batch_reviews API (6 endpoints) | `tests/test_api_batch_reviews.py` | 2 hr |
| 3C.3 | Add tests for settings/credentials (5 endpoints) | `tests/test_api_credentials.py` | 1 hr |
| 3C.4 | Add tests for settings/messaging (7 endpoints) | `tests/test_api_messaging.py` | 2 hr |
| 3C.5 | Add tests for performance API (6 untested endpoints) | `tests/test_api_performance.py` | 2 hr |
| 3C.6 | Add tests for webhook handlers (Telegram + WhatsApp) | `tests/test_api_webhooks.py` | 1 hr |

### 3D: Security Fixes

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 3D.1 | Add Flower authentication | `docker-compose.yml:117` | 15 min |
| 3D.2 | Stop returning webhook secret in response | `api/v1/settings/messaging.py:148` | 15 min |
| 3D.3 | Add URL validation to LeadCreate schema | `schemas/lead.py:17-18` | 15 min |
| 3D.4 | Add unique constraints on suppression domain/phone | Migration | 15 min |

**Validation:** Run full suite + new tests. Verify OpenAPI docs show response schemas for all endpoints.

---

## Phase 4: Frontend Architecture (3-5 days)

**Target: Introduce caching layer, break god components, fix error handling, add code splitting.**

### 4A: Data Caching Layer

| # | Task | Effort |
|---|------|--------|
| 4A.1 | Install and configure SWR or TanStack Query | 1 hr |
| 4A.2 | Migrate `use-page-data.ts` pattern to SWR hooks | 2 hr |
| 4A.3 | Convert all 19 page fetch cycles to use the caching layer | 4 hr |
| 4A.4 | Add visibility-aware polling manager (pause on tab blur) | 2 hr |

### 4B: God Component Decomposition

| # | Component | Split Into | Effort |
|---|-----------|------------|--------|
| 4B.1 | `app/leads/[id]/page.tsx` (550 LOC) | `LeadDetailHeader`, `LeadActions`, `LeadContext`, `LeadSignals` + deduplicate `refreshLeadContext` | 3 hr |
| 4B.2 | `app/responses/page.tsx` (~550 LOC) | `MessageList`, `ComposeArea`, `ThreadDetail` | 3 hr |
| 4B.3 | `app/outreach/page.tsx` (497 LOC) | `DraftList`, `DraftEditor`, `SendConfirmation` | 2 hr |

### 4C: Error Handling

| # | Task | Effort |
|---|------|--------|
| 4C.1 | Create shared `ErrorBoundaryContent` component, replace 16 identical copies | 1 hr |
| 4C.2 | Fix `lib/api/research.ts` to propagate errors instead of returning null | 30 min |
| 4C.3 | Replace ~50 empty catch blocks with shared error utility (console.error + optional toast) | 2 hr |

### 4D: Performance

| # | Task | Effort |
|---|------|--------|
| 4D.1 | Lazy-load Recharts in `performance/page.tsx` and `panel/page.tsx` with `next/dynamic` | 30 min |
| 4D.2 | Move inline types from `ai-office/page.tsx` to `types/ai-office.ts` | 30 min |
| 4D.3 | Fix double pagination in `leads-table.tsx` (trust server pagination) | 1 hr |
| 4D.4 | Fix proxy header spread order in `route.ts:13` | 5 min |

**Validation:** `npx tsc --noEmit` clean. `npx vitest run` passes. Manual smoke test of leads, outreach, responses, dossiers pages.

---

## Phase 5: CI & Observability (1-2 days)

**Target: CI matches pyproject.toml. Coverage baseline. Format enforcement.**

| # | Task | File(s) | Effort |
|---|------|---------|--------|
| 5.1 | Add `ruff format --check app/ tests/` to CI | `ci.yml` | 15 min |
| 5.2 | Add `pytest --cov=app --cov-fail-under=55` to CI | `ci.yml` | 15 min |
| 5.3 | Add pytest markers (`@pytest.mark.slow` for migration test, etc.) | `conftest.py`, `pyproject.toml` | 30 min |
| 5.4 | Remove unused PostgreSQL and Redis service containers from CI | `ci.yml:13-35` | 15 min |
| 5.5 | Add `npx vitest run` to frontend CI (if not already) | `ci.yml` | 15 min |
| 5.6 | Fix brittle tool count assertion | `tests/test_agent_core.py:14` | 5 min |
| 5.7 | Fix dead monkeypatch in weekly report test | `tests/test_weekly_report.py:47-49` | 5 min |
| 5.8 | Fix ambiguous OR assertion in crypto test | `tests/test_crypto.py:29` | 5 min |
| 5.9 | Add `worker-llm` healthcheck to docker-compose | `docker-compose.yml` | 15 min |
| 5.10 | Fix Telegram dispatch to use own settings (not WhatsApp) | `services/notifications/notification_service.py` + migration | 1 hr |

**Validation:** CI pipeline green on all steps. Coverage report generated. `docker-compose up --wait` succeeds with all health checks passing.

---

## Phase 6: Cleanup & Polish (1 day)

**Target: Delete dead code, standardize patterns, resolve minor tech debt.**

| # | Task | Effort |
|---|------|--------|
| 6.1 | Delete `workers/tasks.py` re-export shim, update callers | 15 min |
| 6.2 | Delete/inline `deploy_config_service.py` | 15 min |
| 6.3 | Make private imports public (`_load_leads`, `_normalize_message_id`, `_compute_dedup_hash`) | 30 min |
| 6.4 | Deduplicate `_safe_rate`/`_build_thread_context` helpers | 1 hr |
| 6.5 | Deduplicate `_queue_name` helper (use `_helpers.py` everywhere) | 15 min |
| 6.6 | Remove unused `db` parameter from export functions | 15 min |
| 6.7 | Add idempotency guard to `seed.py` for LeadSource and Territory | 30 min |
| 6.8 | Fix redundant exception tuple in `reply_classification_service.py:171` | 5 min |

**Validation:** Full test suite passes. `ruff check` clean. No broken imports.

---

## Score Progression

| Phase | Completed | Score | Delta |
|-------|-----------|-------|-------|
| Baseline | - | 6.5 | - |
| Phase 0 | Critical fixes | 7.0 | +0.5 |
| Phase 1 | Agent security | 7.5 | +0.5 |
| Phase 2 | Data integrity & perf | 8.0 | +0.5 |
| Phase 3 | API hardening | 8.5 | +0.5 |
| Phase 4 | Frontend architecture | 9.0 | +0.5 |
| Phase 5 | CI & observability | 9.0 | +0.0 (solidifies 9) |
| Phase 6 | Cleanup | 9.0 | +0.0 (polish) |

---

## Estimated Timeline

| Phase | Effort | Dependency |
|-------|--------|------------|
| Phase 0 | 1 day | None |
| Phase 1 | 1-2 days | After Phase 0 |
| Phase 2 | 2-3 days | After Phase 0 |
| Phase 3 | 2-3 days | After Phase 2 |
| Phase 4 | 3-5 days | Independent (frontend) |
| Phase 5 | 1-2 days | After Phase 3 |
| Phase 6 | 1 day | After Phase 5 |

**Phases 1-2 and Phase 4 can run in parallel** (backend vs frontend).

Total: ~12-17 days of focused work.

---

## What NOT to Do

- **Do not rewrite the LLM invocation system.** `invoke_structured` with its 4-tier fallback is production-hardened. Preserve it.
- **Do not migrate to server components yet.** That's a Phase 7+ effort. The caching layer (Phase 4A) provides most of the benefit with far less risk.
- **Do not split the Lead model.** At current scale (1-3k leads), the 27-column model works. Splitting requires a complex migration and JOIN overhead. Revisit at 50k+ leads.
- **Do not add mypy to CI gate yet.** Enable it after a dedicated type-annotation pass. Adding it now would block CI with hundreds of errors.
- **Do not over-abstract.** The duplicated helpers (2 copies each) don't justify a shared utility package. Extract only when a 3rd copy appears or when the divergence causes a bug.
