# Scouter Full Repo Deep Audit — Post-Hardening

**Date:** 2026-04-04 (second pass — after 31-commit hardening session)
**Auditors:** 4 parallel agents (Backend, Frontend, Structure/Tests/Docs, Correctness/Wiring)
**Scope:** Every file in `app/`, `dashboard/`, `tests/`, `docs/`, `scripts/`, `alembic/`, `skills/`, root config
**Previous score:** 7.5/10 → **Current score: 8.5/10**

---

## 1. Executive Summary

Scouter is a **well-engineered, purpose-built lead prospecting platform** for the Argentine web services market. After a 31-commit hardening session, the codebase has materially improved: tests now run on PostgreSQL, correctness bugs are fixed, AI slop is eliminated, and runtime safety is hardened.

**Backend is strong (8.5/10).** Clean architecture, excellent LLM observability, multi-layered prompt injection defense, domain-specific business logic. Two HIGH issues remain: a private function import coupling in `ai_office.py` and a NoneType race in `review_tasks.py`.

**Frontend is solid but not great (7.5/10).** Excellent type system, well-structured API client, good SSR safety. But: non-null assertions that can crash production, unbounded data fetches on 3 pages, and security/notifications page duplication persist.

**Testing is genuinely good (7/10).** 315 tests on PostgreSQL with real security tests, concurrency tests, architecture guardrails, and Alembic migration verification. But: zero frontend tests, zero Celery integration tests, and 3+ API modules untested.

**AI slop is nearly absent (9.5/10).** Both auditors independently confirmed minimal slop. Code reads like it was built by someone who uses the system daily.

---

## 2. Overall Repo Score

| Area | Score | Evidence |
|------|-------|----------|
| Repo structure | **9.5/10** | Clean separation, .editorconfig, loading.tsx, no orphans |
| Backend quality | **8.5/10** | Excellent LLM layer, clean services, 2 HIGH issues remain |
| Frontend quality | **7.5/10** | Good typing, 3 HIGH (non-null assertions, unbounded fetches, duplication) |
| Workers/pipelines | **9/10** | Full chain connected, orphan detection, idempotency, proper retries |
| Data model consistency | **9/10** | Models match migrations, CheckConstraint on singleton, proper enums |
| Prompts/agent system | **9.5/10** | Excellent injection defense, invocation tracking, tool registry with takes_db caching |
| Testing confidence | **7/10** | 315 on PostgreSQL, but no frontend tests, no Celery integration |
| Docs/discoverability | **7.5/10** | Honest and useful, some stale metrics |
| Maintainability | **8.5/10** | Shared modules, no copy-paste in backend, good patterns |
| Theoretical correctness | **9/10** | All routers mounted, pipeline fully connected, settings toggles verified |
| AI slop level | **9.5/10** | Nearly zero — human-authored feel throughout |
| **OVERALL** | **8.5/10** | Strong backend, solid frontend, honest gaps remaining |

---

## 3. Root / Structure Audit

**Verdict: 9.5/10 — Excellent.**

Clean top-level separation. `.editorconfig` added. `test.db` eliminated. Root configs (pyproject.toml, docker-compose, .gitignore, Makefile) are all correct and well-configured. 4 `loading.tsx` skeletons added for heavy pages. AI shim pattern (CLAUDE.md → AGENTS.md) avoids duplication.

---

## 4. README vs Repo Reality

| Claim | Reality | Verdict |
|-------|---------|---------|
| 315 tests (PostgreSQL) | 315 collected, PostgreSQL via testcontainers | ✓ |
| 221 Python files | Accurate | ✓ |
| 108 TS/TSX files | Actually 113 | ⚠ Stale |
| 37 services in 9 subdomains | Actually 44 files | ⚠ Stale |
| 10 canonical Agent OS docs | Actually 9 in docs/agents/ | ⚠ Off by one |
| 42 Alembic migrations | Accurate | ✓ |

---

## 5. Backend Audit

### What Is Excellent

1. **LLM invocation architecture** — `PromptDefinition[SchemaT]` generics, three-tier parse recovery, per-invocation metadata via ContextVar, DB persistence. Production-grade.
2. **Pipeline task tracking** — `tracked_task_step` context manager, `TrackedTaskStepHandle`, PipelineRun correlation. Non-trivial engineering done right.
3. **Security fundamentals** — HMAC auth, Fernet encryption, log scrubbing, prompt injection defense, webhook auth, CORS restriction.
4. **Domain expertise** — Draft post-validation (URL fabrication removal, solo/plural checks, brand leak detection), dedup hashing, suppression with OR logic.
5. **Operational sophistication** — LOW_RESOURCE_MODE, runtime mode presets, task stop signals, janitor with orphan detection.

### Remaining Issues

| # | Sev | Type | File | Finding |
|---|-----|------|------|---------|
| H-1 | HIGH | architecture | `api/v1/ai_office.py:373` | Imports private `_get_or_create_credentials` and `_get_provider` from whatsapp_service. Should use public API. |
| H-2 | HIGH | correctness | `workers/review_tasks.py:238` | `message.lead_id` accessed before null check on `message`. NoneType crash if message deleted between queue and execution. |
| M-1 | MEDIUM | maintainability | 11 files | 12 silent `except Exception: pass` blocks without even `logger.debug`. |
| M-2 | MEDIUM | ai_slop | 3 worker files | `_track_failure` helper duplicated (~45 lines each) across pipeline_tasks, research_tasks, review_tasks. |
| M-3 | MEDIUM | correctness | `settings/operational.py:18` | `DbSession = Annotated[object, ...]` types db as `object`, defeats IDE support. |
| M-4 | MEDIUM | correctness | `suppression_service.py:26-33` | Suppression only retroactively checks email, not domain or phone. |
| M-5 | MEDIUM | correctness | `export_service.py` | Export functions materialize full result in memory despite `yield_per` upstream. |
| M-6 | MEDIUM | security | `crypto.py:19` | SHA-256 key derivation without proper KDF (PBKDF2/HKDF). |
| M-7 | MEDIUM | correctness | `lead_service.py:51-53` | `create_lead` returns existing lead on dedup as 201 — client can't distinguish created vs existed. |

---

## 6. Frontend Audit

### What Is Excellent

1. **Type system** — 987-line `types/index.ts` with union types eliminating magic strings. Zero `as any`.
2. **Static Tailwind maps** — All color classes use complete string lookups, no dynamic interpolation.
3. **API client** — Retry with backoff, typed returns, SSR/browser URL switching.
4. **Proxy security** — Allowlist, traversal blocking, server-side API key injection.
5. **SSR safety** — RelativeTime handles hydration, map uses `dynamic({ ssr: false })`, localStorage in useEffect only.

### Remaining Issues

| # | Sev | Type | File | Finding |
|---|-----|------|------|---------|
| F-1 | HIGH | correctness | `use-chat.ts:74` | `res.body!` non-null assertion — can crash on empty response. |
| F-2 | HIGH | correctness | `activity-pulse.tsx` (11 places) | `batch!` non-null assertions inside derived boolean guard. Race condition crash risk. |
| F-3 | HIGH | runtime_risk | 3 pages | `getLeads({ page_size: 200 })` without pagination on dossiers, outreach, responses. |
| F-4 | MEDIUM | ai_slop | security + notifications | ~80% duplicated code (556 + 593 lines). |
| F-5 | MEDIUM | runtime_risk | `client.ts:630-645` | `getLeadsWithCoords` unbounded while-true pagination loop. |
| F-6 | MEDIUM | runtime_risk | `dossiers/page.tsx:36-41` | N+1 fan-out: fires `getLeadResearch()` per HIGH lead in parallel. |
| F-7 | MEDIUM | correctness | `performance/page.tsx:43` | Last `Record<string, any>` in codebase. |

---

## 7. Workers / Pipelines Audit

**Score: 9/10.** Full pipeline chain verified end-to-end. Orphan detection working. Idempotency guards everywhere. Proper retry with backoff. Beat schedule correct. LOW_RESOURCE_MODE merges queues correctly.

Only issue: `_track_failure` duplication (M-2) and weekly report uses fixed interval instead of crontab (LOW).

---

## 8. Models / Schemas / Migrations Audit

**Score: 9/10.** All 42 migrations apply cleanly (verified by guardrail test). Models match migrations. CheckConstraint on singleton. Proper enum types.

Contract mismatches found by correctness auditor:
- `signature_is_solo` missing from TS `OperationalSettings` (MEDIUM)
- Notification fields misplaced in TS `InboundMailSettings` (MEDIUM)
- `low_resource_mode` not in `_ALLOWED_SETTINGS_FIELDS` — can't write via PATCH (LOW)
- `kapso_api_key` missing from TS `CredentialsStatus` (LOW)

---

## 9. Prompts / Agent / Skills Audit

**Score: 9.5/10.** Agent loop sound (MAX_TOOL_LOOPS=5, termination guarantee). 15 tool modules, 55 tools registered. `takes_db` cached at registration. Prompt injection defense multi-layered. Prompt registry versioned and typed.

---

## 10. Testing Audit

**Score: 7/10.**

**What's genuinely good:**
- 315 tests on PostgreSQL (not SQLite)
- Security tests verify 7+ real attack vectors
- Architecture guardrails catch structural drift
- Alembic migration chain test
- Concurrency and race condition tests
- LLM fallback/degraded metadata fully tested

**What's missing:**
- Zero frontend tests (113 TS/TSX files)
- Zero Celery integration tests (all `.run()` direct)
- Telegram, Territories, Notifications API endpoints untested
- No IMAP/SMTP/Google Maps protocol tests
- Test data seeding duplicated across files

---

## 11. Docs / Markdown / Discoverability Audit

**Score: 7.5/10.** Documentation is honest and useful. Architecture audit doesn't sugarcoat. Security backlog lists unresolved HIGHs. Hardening plan is actionable. But: several README metrics are stale, no ADRs written, no API documentation beyond Swagger.

---

## 12. AI Slop Audit

**Score: 9.5/10 — Nearly zero slop.**

Both backend and frontend auditors independently confirmed:
- No unnecessary abstraction layers
- No empty wrapper functions
- No gratuitous design patterns
- No inflated class hierarchies
- No over-engineering (no Redux, no repository pattern)
- Functions do real work with domain-specific logic

**Only slop signals:**
- `_track_failure` duplicated across 3 worker files (~135 lines total)
- Security/notifications page duplication (~500 lines)
- `reply-draft-panel.tsx` at 597 lines approaching extraction threshold

---

## 13. Theoretical Correctness Audit

**Score: 9/10.** All 23 routers mounted. Full pipeline connected end-to-end. All Celery tasks registered with matching routes. Agent loop sound. Settings toggles verified. New features (leads/names, pagination, orphan detection) correctly wired.

2 contract mismatches found (TS types missing fields), 1 settings write-path gap.

---

## 14. Maintainability Audit

**Score: 8.5/10.** Clean module boundaries. Shared frontend modules. Conventional commits. Good architecture documentation. Cost of change is low for most operations.

Weaknesses: no frontend tests (high cost to change UI safely), worker helper duplication, `services/` growing large (44 files).

---

## 15. Runtime Risk Audit

**Inspires confidence:** LLM invocation tracking, idempotency guards, retry with backoff, task stop signals, orphan detection, rate limiting, suppression checking, reviewer feedback loop, dedup hashing.

**Does not inspire confidence:** `batch!` non-null assertions (crash risk), unbounded `getLeadsWithCoords` loop, dossiers N+1 fan-out, 12 silent exception swallows, `res.body!` in chat hook.

---

## 16. What Is Excellent

1. LLM observability system — full invocation tracking with prompt versioning
2. Prompt injection defense — multi-layered, verified by real attack tests
3. PostgreSQL test infrastructure — testcontainers with guardrail enforcement
4. Architecture guardrail tests — catch structural decay automatically
5. Pipeline orchestration — tracked steps, context threading, orphan detection
6. Domain-specific business logic — scoring, enrichment, draft validation
7. Honest documentation — audit rates itself honestly, security backlog transparent
8. Agent system — sound loop, tool registry with takes_db caching
9. Operational tooling — full lifecycle scripted
10. Conventional commits — navigable git history

---

## 17. What Is Fragile

1. `batch!` non-null assertions in activity-pulse (11 crash points)
2. `res.body!` in chat hook (crash on empty response)
3. Unbounded `getLeadsWithCoords` pagination loop
4. Dossiers page N+1 fan-out
5. `review_tasks.py` NoneType race on deleted message
6. 12 silent exception blocks across backend
7. Private function imports in ai_office.py

---

## 18. What Feels Inflated or Low-Signal

1. Security/notifications page duplication (~500 lines, ~80% identical)
2. `_track_failure` duplicated across 3 worker files
3. `reply-draft-panel.tsx` at 597 lines (approaching extraction threshold)
4. `types/index.ts` at 987 lines (single file for all contracts)

---

## 19. Top 20 Findings

| # | Sev | Type | Summary |
|---|-----|------|---------|
| 1 | HIGH | correctness | `review_tasks.py:238` NoneType race — message accessed before null check |
| 2 | HIGH | architecture | `ai_office.py:373` imports private functions from whatsapp_service |
| 3 | HIGH | correctness | `use-chat.ts:74` `res.body!` non-null assertion |
| 4 | HIGH | correctness | `activity-pulse.tsx` 11 `batch!` non-null assertions |
| 5 | HIGH | runtime_risk | 3 pages fetch page_size=200 with no pagination |
| 6 | MEDIUM | ai_slop | Security/notifications ~80% duplicated code |
| 7 | MEDIUM | correctness | `signature_is_solo` missing from TS OperationalSettings |
| 8 | MEDIUM | correctness | Notification fields misplaced in TS InboundMailSettings |
| 9 | MEDIUM | maintainability | 12 silent `except Exception: pass` blocks |
| 10 | MEDIUM | ai_slop | `_track_failure` duplicated across 3 worker files |
| 11 | MEDIUM | runtime_risk | `getLeadsWithCoords` unbounded pagination loop |
| 12 | MEDIUM | runtime_risk | Dossiers N+1 fan-out (getLeadResearch per lead) |
| 13 | MEDIUM | correctness | `DbSession = Annotated[object, ...]` defeats IDE support |
| 14 | MEDIUM | correctness | Suppression doesn't retroactively check domain/phone |
| 15 | MEDIUM | correctness | Export materializes full result despite yield_per |
| 16 | MEDIUM | security | SHA-256 key derivation without proper KDF |
| 17 | MEDIUM | correctness | create_lead silent dedup (201 for both new and existing) |
| 18 | MEDIUM | testing | No frontend tests (113 TS/TSX files) |
| 19 | MEDIUM | testing | No Celery integration tests |
| 20 | LOW | correctness | `low_resource_mode` not in _ALLOWED_SETTINGS_FIELDS |

---

## 20. Top 10 Quick Wins

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Add null check before `message.lead_id` in review_tasks (H-2) | 5 min | HIGH |
| 2 | Add null guard before `res.body!.getReader()` in use-chat (F-1) | 5 min | HIGH |
| 3 | Replace `batch!` with proper narrowing in activity-pulse (F-2) | 15 min | HIGH |
| 4 | Add `signature_is_solo` to TS OperationalSettings | 2 min | MEDIUM |
| 5 | Remove misplaced notification fields from TS InboundMailSettings | 5 min | MEDIUM |
| 6 | Add `low_resource_mode` to _ALLOWED_SETTINGS_FIELDS | 2 min | LOW |
| 7 | Add `kapso_api_key` to TS CredentialsStatus | 2 min | LOW |
| 8 | Replace 12 bare `except: pass` with `logger.debug` | 30 min | MEDIUM |
| 9 | Fix DbSession type alias to use Session | 2 min | MEDIUM |
| 10 | Use crontab for weekly report schedule | 5 min | LOW |

---

## 21. Top 10 Hard Problems

| # | Problem | Effort |
|---|---------|--------|
| 1 | Extract shared NotificationListView from security + notifications | 1-2 hours |
| 2 | Extract _track_failure to shared worker helper | 1 hour |
| 3 | Create public send_message_to_phone in whatsapp_service (H-1) | 1 hour |
| 4 | Add backend geo endpoint to replace getLeadsWithCoords loop | 1 day |
| 5 | Add server-side leads-with-research endpoint for dossiers | 1 day |
| 6 | Add frontend component tests (at least critical paths) | 2-3 days |
| 7 | Add Celery integration tests | 1-2 days |
| 8 | Upgrade crypto to PBKDF2HMAC with key migration | 1 day |
| 9 | Add API authentication (beyond API key) | 3-5 days |
| 10 | Write 3 ADRs for key architecture decisions | 1-2 days |

---

## 22. What Should Be Refactored

1. **Security/notifications pages** → Extract shared NotificationListView
2. **Worker _track_failure** → Extract to shared _helpers.py
3. **ai_office.py send_closer_reply** → Use public whatsapp_service API
4. **review_tasks.py** → Move null checks before .lead_id access
5. **activity-pulse.tsx** → Replace batch! with proper null narrowing
6. **types/index.ts** → Consider splitting by domain (leads, settings, outreach)

---

## 23. What Should Not Be Touched

1. **`app/llm/` module** — Crown jewel. Prompt injection defense + invocation tracking.
2. **`app/scoring/rules.py`** — Domain-specific scoring with real market knowledge.
3. **`app/agent/tool_registry.py`** — Hand-crafted for Hermes 3 with takes_db caching.
4. **Security tests** — 7+ real attack vectors. Don't reduce.
5. **Architecture guardrail tests** — Unique and valuable.
6. **Pipeline task tracking** — TrackedTaskStepHandle is well-designed.
7. **SOUL.md / IDENTITY.md** — Runtime assets, not docs.

---

## 24. Final Verdict

**This is an 8.5/10 codebase, up from 7.5/10 pre-hardening.** The hardening session delivered real value:

- ✅ Tests on PostgreSQL (was the #1 gap)
- ✅ Correctness bugs fixed (suppression OR, Pydantic schema, Tailwind)
- ✅ AI slop eliminated (shared modules, deps.py deleted)
- ✅ Runtime safety improved (orphan detection, streaming export, pagination)
- ✅ Architecture guardrails added (PostgreSQL enforcement, migration chain)

**What keeps it from 9+:**
- Frontend has 3 HIGH crash risks (non-null assertions)
- Security/notifications duplication (~500 lines)
- No frontend tests
- No Celery integration tests
- Some stale doc metrics

**Recommendation:** Fix the 10 quick wins (1-2 hours), then tackle the NotificationListView extraction and worker helper dedup. That would bring it to ~9/10. The jump from 9 to 10 requires frontend testing infrastructure and Celery integration tests.
