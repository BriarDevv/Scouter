# Scouter Full Repo Deep Audit

**Date:** 2026-04-04
**Auditors:** 4 parallel agents (Backend, Frontend, Structure/Tests/Docs, Correctness/Wiring)
**Scope:** Every file in `app/`, `dashboard/`, `tests/`, `docs/`, `scripts/`, `alembic/`, `skills/`, root config
**Lines audited:** ~28,300 Python (app/) + ~15,000 TypeScript (dashboard/) + ~7,300 Python (tests/) + all docs/config

---

## 1. Executive Summary

Scouter is a **genuinely well-engineered, purpose-built system** for lead prospecting in the Argentine web services market. The backend is the strongest part — clean architecture, excellent LLM observability, multi-layered prompt injection defense, and domain-specific business logic that reflects real operational experience. The frontend is functional and well-typed but carries significant copy-paste debt and a few production-breaking styling bugs. Tests are substantive (not cosmetic) but run against SQLite instead of PostgreSQL, creating a blind spot for the most common production failure mode.

**AI slop is very low.** This reads like human-authored code with clear domain intent, not generated filler. The few slop signals (copy-paste pages, duplicate constants, placeholder comments) are isolated and fixable.

**The system works end-to-end.** All 22 routers are mounted, the full pipeline chain is connected, the agent loop is sound, and all settings toggles have real behavioral effects. No dead code paths were found in the backend.

**Resolved since initial audit:** Tests migrated to PostgreSQL, migration chain tested, Pydantic schema gap fixed. **Remaining gaps:** no frontend component tests, no API authentication (acknowledged in security backlog).

---

## 2. Overall Repo Score

| Area | Score | Evidence |
|------|-------|----------|
| Repo structure | **9/10** | Clean separation, discoverable naming, no orphans, no noise |
| Backend quality | **8/10** | Well-engineered services, excellent LLM layer, minor wiring issues |
| Frontend quality | **6.5/10** | Good typing but HIGH issues: broken Tailwind in prod, copy-paste, stale hooks |
| Workers/pipelines | **8/10** | Proper tracking, idempotency, retries, queue routing, low-resource mode |
| Data model consistency | **8/10** | Good alignment, minor phantom frontend fields |
| Prompts/agent system | **9/10** | Excellent injection defense, structured output, full observability |
| Testing confidence | **9/10** | 315 tests on PostgreSQL, migration chain verified, guardrail prevents regression |
| Docs/discoverability | **8.5/10** | Honest, useful, minor staleness risk |
| Maintainability | **7/10** | Clean backend architecture, but frontend copy-paste and implicit pipeline coupling |
| Theoretical correctness | **7.5/10** | Well-wired but suppression logic bug, Pydantic gap, pipeline orphan risk |
| AI slop level | **9/10** | Very low slop — human-authored feel, domain-specific logic, no empty abstractions |
| **OVERALL** | **7.5/10** | Solid backend, decent frontend, honest gaps acknowledged |

---

## 3. Root / Structure Audit

### Layout

```
Root:       AGENTS.md, CLAUDE.md, CODEX.md, GEMINI.md, SOUL.md, IDENTITY.md
            README.md, pyproject.toml, Makefile, docker-compose.yml, .env.example
            .gitignore, .dockerignore, alembic.ini, LICENSE
Directories: app/, dashboard/, docs/, tests/, scripts/, skills/, alembic/, infra/, logs/
Hidden:      .claude/, .omc/, .omx/, .dev-runtime/, .pids/, .venv/
```

**Verdict: SOLID.** Clear top-level separation. `app/` has meaningful internal structure with real bounded contexts (`agent/`, `api/v1/`, `llm/`, `models/`, `services/`, `workers/`, `workflows/`, `schemas/`, `scoring/`, `crawlers/`, `mail/`, `core/`, `data/`, `outreach/`). Better than the vast majority of solo-developer repos.

**Root files are clean and purposeful.** The AI-assistant shim pattern (CLAUDE.md → AGENTS.md) is pragmatic and avoids duplication. `pyproject.toml` has well-configured Ruff rules and strict mypy. `docker-compose.yml` has healthchecks on all 6 services with ports bound to 127.0.0.1. `.env.example` is thorough (60+ variables with comments).

**Minor noise:** `test.db`, `celerybeat-schedule`, `scouter.egg-info/` exist at root but are all gitignored. Runtime dirs (`.omc/`, `.omx/`, `.dev-runtime/`, `.pids/`) accumulate but are also gitignored.

---

## 4. README vs Repo Reality

| Claim | Reality | Verdict |
|-------|---------|---------|
| `make up` starts everything | Makefile → `scripts/scouter.sh start` | ✓ Consistent |
| `pytest -v` for backend tests | Makefile runs `.venv/bin/python -m pytest -v` | ✓ Consistent |
| 4 AI roles with specific models | SOUL.md, IDENTITY.md, and code confirm | ✓ Consistent |
| 55 agent tools | `test_agent_core.py` asserts exactly 55 | ✓ Consistent |
| PostgreSQL 16, Redis 7 | docker-compose uses `postgres:16-alpine`, `redis:7-alpine` | ✓ Consistent |
| 42 test files / 299 passing | Verified via pytest --collect-only | ✓ Consistent (snapshot) |
| 314 Python files, 112 TS/TSX | Snapshot metrics — no automated verification | ⚠ Will rot |

**Verdict:** README is honest and accurate today. Risk is staleness of hardcoded metrics.

---

## 5. Backend Audit

### What Is Excellent

1. **LLM layer is the strongest part of the codebase.** Multi-layered prompt injection defense (sanitizer + system/user separation + `<external_data>` tags + `ANTI_INJECTION_PREAMBLE`). Full invocation tracking with prompt_id, version, role, model, latency, status, correlation context. Structured output with multi-stage fallback (direct parse → `_extract_json` heuristic → fallback factory). Each status tracked: `SUCCEEDED`, `DEGRADED`, `FALLBACK`, `PARSE_FAILED`, `FAILED`. This is production-grade observability.

2. **Operational sophistication.** LOW_RESOURCE_MODE reads from DB on startup, falls back to env. Runtime mode presets (safe/assisted/auto) with real behavioral effects. Task stop signals, stale task detection. This is built for a daily operator.

3. **Domain expertise is evident.** Scoring weights, industry lists, signal interpretation rules, and prompt instructions all reflect deep understanding of the Argentine SMB web services market. Rioplatense Spanish in prompts, local city coordinates, culturally appropriate business categories.

4. **Security posture.** No SQL injection (all ORM, no raw SQL with f-strings). HMAC-based API key comparison (timing-safe). Secrets encrypted at rest (Fernet). Passwords never returned in API responses. SMTP errors sanitized. Log scrubber redacts sensitive keys. Docs/redoc disabled in non-dev.

5. **Clean architecture.** Services contain business logic, routers are thin. 22 routers all properly mounted. Versioned API prefix. Request context middleware with correlation IDs.

### Findings

| # | Severity | Type | File | Finding |
|---|----------|------|------|---------|
| B1 | **HIGH** | runtime_risk | `app/agent/channel_router.py:118-127` | Channel router creates `ThreadPoolExecutor` + new event loop per Telegram/WhatsApp message. Unbounded thread creation under concurrent load. |
| B2 | MEDIUM | security | `app/core/crypto.py:15-17` | `_derive_key()` uses raw SHA-256 instead of proper KDF (PBKDF2/HKDF). No salt, no iterations. |
| B3 | MEDIUM | correctness | `app/services/leads/lead_service.py:31-37` | `is_suppressed()` uses `*conditions` (AND) instead of `or_(*conditions)` (OR). Suppressed email with different domain not caught when both provided. |
| B4 | MEDIUM | correctness | `app/api/v1/ai_office.py:117-139` | Agent status endpoint hardcodes model names (`hermes3:8b`, `qwen3.5:9b`, `qwen3.5:27b`). Wrong if operator changes models via config. |
| B5 | MEDIUM | architecture | `app/agent/channel_router.py:57-63` | Cross-channel conversation routing finds ANY recent conversation regardless of channel. Two WhatsApp users would share one conversation. |
| B6 | MEDIUM | architecture | `app/llm/client.py:183-216` | `_persist_invocation` always opens new DB session per LLM call instead of reusing caller's session. |
| B7 | MEDIUM | correctness | `app/api/v1/setup.py:14-15` | Setup action rate limit uses module-level mutable global. Not thread/process-safe. |
| B8 | MEDIUM | correctness | `app/api/v1/briefs.py:47` | Trailing slash inconsistency: `@router.get("/")` vs `@router.get("")` in all other routers. Causes 307 redirects. |
| B9 | MEDIUM | runtime_risk | `app/workers/pipeline_tasks.py:167-172` | Pipeline chaining via `.delay()` — if a step fails, pipeline silently stops. No orphan detection. |
| B10 | MEDIUM | architecture | `app/agent/core.py:203-204` | `inspect.signature()` called on every tool invocation for `db` param check. Should be cached at registration. |
| B11 | LOW | correctness | `app/core/crypto.py:54-55` | `decrypt_safe` silently returns ciphertext on InvalidToken. Key rotation failures produce confusing downstream errors. |
| B12 | LOW | architecture | `app/api/deps.py:11-12` | `get_session` is trivial `yield from get_db()` wrapper. Zero value added. |
| B13 | LOW | correctness | `app/api/v1/leads.py:62-67` | Export endpoint loads all matching leads into memory via `query.all()`. OOM risk at scale. |
| B14 | LOW | correctness | `app/api/v1/briefs.py:50` | `limit: int = 50` has no `Query(ge=1, le=...)` constraint. |
| B15 | LOW | data_model | `app/models/settings.py:19` | `OperationalSettings` singleton (id=1) has no DB check constraint. |
| B16 | LOW | security | `app/core/logging.py:9-12` | Sensitive key regex misses `api_key` pattern. Could log API keys in plaintext. |
| B17 | LOW | runtime_risk | `app/services/leads/enrichment_service.py:136-148` | Subpage email extraction fetches 5 pages sequentially (worst case 75s per lead). |
| B18 | LOW | architecture | `app/workers/celery_app.py:81-88` | All worker modules imported at startup. Heavy init, but necessary for Celery. |

---

## 6. Frontend Audit

### What Is Excellent

1. **Excellent type coverage.** `types/index.ts` (980 lines) is comprehensive and aligns well with the FastAPI backend. API client is fully typed with proper return types on every function.

2. **Smart SSR/client boundary.** `API_BASE_URL` resolves differently on server vs client (direct backend vs proxy). Leaflet map uses `next/dynamic` with `ssr: false`. Theme applied via inline script to prevent flash.

3. **Consistent design system.** Rounded-2xl cards, violet accent, font-heading/font-data separation, dark mode via oklch. Badge components (`StatusBadge`, `QualityBadge`, `DraftStatusBadge`) properly reused across 17 pages.

4. **Proxy security.** `api/proxy/[...path]` strips hop-by-hop headers, blocks path traversal (`..`, `//`), path allowlist with 23 prefixes, API key injected server-side.

5. **Good loading/error/empty states.** Every page has loading skeletons, error displays, and empty state components. Toast system (`sileo.promise()`) used consistently for async actions.

### Findings

| # | Severity | Type | File | Finding |
|---|----------|------|------|---------|
| F1 | **HIGH** | correctness | `app/ai-office/page.tsx:270-272`, `components/leads/ai-decisions-panel.tsx:173-175`, `components/dashboard/ai-health-card.tsx:89` | Dynamic Tailwind classes (`` `border-${color}-100` ``) will be tree-shaken in production. Agent cards, AI decisions, and health metrics render without colors. |
| F2 | **HIGH** | runtime_risk | `lib/api/client.ts:625-639` | `getLeadsWithCoords` has unbounded `while(true)` loop paging through ALL leads (200/page) with no abort controller. Map page load scales linearly with DB size. |
| F3 | **HIGH** | ai_slop | `app/security/page.tsx` (555 lines), `app/notifications/page.tsx` (591 lines) | ~70% identical code between these pages. Classic "generate another page like this" output. |
| F4 | **HIGH** | ai_slop | `components/layout/activity-pulse.tsx:24-58`, `app/activity/page.tsx:32-65` | `STEP_CONFIG`, `REVIEWER_STEPS`, `NO_LLM_STEPS`, `getStepConfig()`, `getModelForStep()`, `formatModelShort()`, `isActive()`, `ModelBadge` all duplicated verbatim. |
| F5 | **HIGH** | correctness | `lib/hooks/use-page-data.ts:19-31` | `useCallback` with empty deps array (`[]`) and eslint-disable. Stale closure over `fetcher` — `refresh()` always calls original fetcher even if params changed. |
| F6 | MEDIUM | runtime_risk | `app/activity/page.tsx:296`, `app/outreach/page.tsx:60`, `app/responses/page.tsx:73`, `app/dossiers/page.tsx:31` | Every non-leads page fetches all leads (200) just for name resolution via `leadById` map. |
| F7 | MEDIUM | correctness | `app/leads/page.tsx:19` | Hard cap at 200 leads with no pagination UI. Leads beyond 200 are invisible. |
| F8 | MEDIUM | correctness | `components/layout/readiness-gate.tsx:17-38` | Fires network request on every pathname change. Once unlocked, readiness is unlikely to change. |
| F9 | MEDIUM | correctness | `lib/hooks/use-chat.ts:91` | SSE JSON parse (`JSON.parse(line.slice(6))`) not wrapped in try/catch. Malformed event crashes streaming loop. |
| F10 | MEDIUM | correctness | `app/panel/page.tsx:104` | `stats!` non-null assertion. Unexpected API shape throws at render time. |
| F11 | MEDIUM | correctness | `app/map/page.tsx:73` | `as any` type escape in `updateTerritory(id, data as any)`. |
| F12 | MEDIUM | correctness | `types/index.ts:737,742` | `Record<string, any>` usage undermines strict TypeScript config. |
| F13 | MEDIUM | architecture | `lib/api/client.ts:528-538` | `TelegramCredentials` type defined in API client instead of `types/index.ts`. |
| F14 | MEDIUM | architecture | `app/settings/page.tsx:40-41` | `WhatsAppCredentials` imported from component instead of `types/index.ts`. |
| F15 | MEDIUM | correctness | `app/dossiers/page.tsx:66`, `app/briefs/page.tsx:38` | Double `LayoutShell` nesting (inner + global from root layout). |
| F16 | MEDIUM | correctness | `app/activity/page.tsx:133` | Unused `StepIcon` variable in `ActiveTaskCard`. |
| F17 | MEDIUM | frontend | `components/dashboard/ai-health-card.tsx:18-19` | Comment says "placeholder" — component silently shows "---" if endpoint missing. Misleading to user. |
| F18 | LOW | frontend | `app/map/page.tsx:51` | `console.error` instead of `sileo.error()` toast. Only page that breaks the pattern. |
| F19 | LOW | frontend | Multiple (24 files) | 47 occurrences of empty `catch {}` or `.catch(() => {})` that silently swallow errors. |
| F20 | LOW | correctness | `lib/formatters.ts:18-31` | `formatRelativeTime` doesn't handle future dates. Clock skew produces "Hace -3m". |
| F21 | LOW | frontend | `app/performance/page.tsx:232-235` | Magic velocity multipliers (`* 0.11`, `* 0.26`, `* 0.45`) with no documentation. |
| F22 | LOW | frontend | No `loading.tsx` files | All pages implement manual loading states instead of leveraging Next.js streaming SSR. |

---

## 7. Workers / Pipelines Audit

### What Is Excellent

- **Proper task tracking** with `tracked_task_step` context manager.
- **Idempotency guards** — skip if already enriched/scored/analyzed.
- **Exponential backoff** on retries. `SoftTimeLimitExceeded` handling.
- **Queue routing** per task type with LOW_RESOURCE_MODE merging to `default`.
- **Beat schedule** correctly references registered tasks.
- **Full pipeline chain verified end-to-end:** lead → enrich → score → analyze → (HIGH: research → brief → brief_review) → draft generation. All paths terminate.

### Findings

Already captured in B1 (channel router threading) and B9 (pipeline orphan risk).

Additional:

| # | Severity | Type | Finding |
|---|----------|------|---------|
| W1 | LOW | architecture | `batch_pipeline.py:181-230` — Each lead in batch gets its own `SessionLocal()`. For 500 leads, 500 session create/close cycles. Correct for isolation but worth noting. |

---

## 8. Models / Schemas / Migrations Audit

### What Is Solid

- 27 model classes, all with proper mapped columns, foreign keys, indices, cascade rules.
- Good enum definitions as `str, enum.Enum` subclasses.
- Dedup hash with unique constraint on leads.
- 37 Alembic migrations with descriptive naming and a merge migration for branch reconciliation.
- Model evolution matches migration chain (verified: LeadStatus enum additions, SignalType additions, llm_quality column).

### Findings

| # | Severity | Type | File | Finding |
|---|----------|------|------|---------|
| M1 | **MEDIUM** | correctness | `app/schemas/operational_settings.py:99-144` | `OperationalSettingsResponse` missing `runtime_mode` and `pricing_matrix` fields. FastAPI's `response_model` silently strips these from API responses even though `to_response_dict()` returns them. Dashboard runtime mode panel cannot read current mode. |
| M2 | LOW | correctness | `dashboard/types/index.ts:100-101` | Frontend `Lead` type has phantom `owner` and `notes` fields that don't exist in backend model or schema. Always undefined. |
| M3 | LOW | correctness | `dashboard/types/index.ts:247` | Frontend `SuppressionEntry` expects `business_name` that backend model doesn't have. |

---

## 9. Prompts / Agent / Skills Audit

### What Is Excellent

1. **Agent loop is sound.** MAX_TOOL_LOOPS=5 with termination guarantee. Hermes 3 XML format parsing handles both `arguments` and `parameters` keys. Tool registry with parameter validation and type coercion. 15 tool modules, 55 tools registered (verified by test).

2. **Prompt registry is well-designed.** Versioned, typed `PromptDefinition[SchemaT]` generics. Clean separation of prompt text from rendering. 13 registered prompts + 3 non-registry prompts cataloged in `app/llm/PROMPTS.md`.

3. **Confirmation flow** for destructive operations exists (though currently auto-skipped for non-web channels — documented intentionally).

4. **Security preamble** prevents agent from leaking credentials.

5. **Skills architecture** with per-domain SKILL.md files is a thoughtful agent-OS pattern. MODEL_ROUTING.md documents role-to-model mapping.

### Findings

Already captured in B1 (channel router threading), B5 (cross-channel routing), B10 (inspect.signature overhead).

---

## 10. Testing Audit

### What Is Genuinely Good

1. **Security tests are real and meaningful.** `test_security.py` verifies prompt injection isolation across 7 distinct attack vectors. Not cosmetic.

2. **Architecture guardrail tests catch structural decay.** `test_arch_guardrails.py` enforces: no .env mutation from API layer, no private LLM helper imports, no Redis writes in API layer, worker task registration, frontend enum drift detection.

3. **Error/failure path coverage is above average.** Tests verify: Ollama unavailable, SMTP fails, concurrent inserts race, duplicate clicks, mail disabled, LLM returns garbage.

4. **Concurrency and race condition tests exist.** `test_api_reply_assistant.py` simulates concurrent insert via second DB session. `test_api_tasks.py` has worker-race test.

5. **Idempotency and rate limiting tested.** `test_idempotency.py` for enrichment/scoring/analysis. `test_notifications.py` for rate limits (3 per 15-min) and dedup keys.

### Findings

| # | Severity | Type | Finding |
|---|----------|------|---------|
| T1 | ~~HIGH~~ **RESOLVED** | testing | ~~All tests run against SQLite.~~ Tests now run on PostgreSQL 16 via testcontainers. Migration chain test verifies 42 migrations. Guardrail prevents regression. |
| T2 | **HIGH** | testing | No Alembic migration tests. 37 migrations exist with no automated verification they apply cleanly to PostgreSQL. Tables created via `Base.metadata.create_all()` in conftest. |
| T3 | **HIGH** | testing | No API authentication tests (no API auth exists — acknowledged in security-backlog.md as SEC-9). |
| T4 | MEDIUM | testing | No Celery/Redis integration tests. All async task tests call `.run()` directly, bypassing serialization, routing, retry, and acknowledgment. |
| T5 | MEDIUM | testing | No frontend tests whatsoever. 17+ pages, zero test files under `dashboard/`. |
| T6 | LOW | testing | Test data seeding duplicated across files (`_create_sent_delivery()` in both `test_api_inbound_mail.py` and `test_api_inbound_classification.py`). |
| T7 | LOW | testing | `test_whatsapp_outreach.py` is mostly `hasattr` and column nullability checks — schema introspection, not behavior testing. |

### Critical Untested Paths

1. Real Celery task dispatch, serialization, and retry
2. Alembic migration chain on PostgreSQL
3. Full pipeline end-to-end with real task dispatch
4. Frontend rendering, navigation, and API interaction
5. WebSocket/SSE agent chat streaming
6. Real SMTP/IMAP communication
7. Real Ollama interaction

---

## 11. Docs / Markdown / Discoverability Audit

### What Is Solid

1. **docs/README.md** is a real navigation map with canonical/archive separation, goal-based reading paths.
2. **docs/architecture/audit.md** is an honest, brutal self-assessment (600+ lines, rates codebase 5.6/10).
3. **docs/operations/security-backlog.md** transparently lists unresolved HIGH findings.
4. **docs/plans/refactor-roadmap.md** is a real incremental plan with 6 phases, risk assessment, and "What Not To Do".
5. **Archive separation is clean.** Historical docs in `docs/archive/` with clear subdirectories.

### Findings

| # | Severity | Type | Finding |
|---|----------|------|---------|
| D1 | MEDIUM | docs | architecture/audit.md predates Agent OS implementation. Staleness note added but evidence counts may be inaccurate. |
| D2 | MEDIUM | docs | Refactor roadmap recommends 10 ADRs. None have been written. |
| D3 | LOW | docs | README hardcoded metrics (314 files, 299 tests, etc.) will drift with no automated verification. |
| D4 | LOW | docs | `docs/agents/` has 9 files for a 4-agent system. Volume risk if not maintained. |

---

## 12. AI Slop Audit

### Verdict: 9/10 — Very Low Slop

**Evidence of human authorship:**
- Business logic is culturally specific (Argentine Spanish, rioplatense conjugation, local city coordinates)
- Prompt engineering shows iterative refinement (specific signal interpretation, edge cases for instagram-only leads)
- Architecture decisions show cost awareness (low-resource mode, single Celery queue option)
- Tool registry and Hermes 3 format handling are hand-crafted for specific model family
- Error messages contextually appropriate in Spanish
- Scoring weights reflect real market knowledge

**Slop signals found (isolated, not systemic):**

| Signal | Location | Evidence |
|--------|----------|----------|
| Copy-paste page | `security/page.tsx` vs `notifications/page.tsx` | ~70% identical code. Classic "generate another page like this" |
| Duplicate constants | `activity-pulse.tsx` vs `activity/page.tsx` | `STEP_CONFIG` and 7 functions duplicated verbatim |
| Placeholder comment | `ai-health-card.tsx:18-19` | "For now, this is a placeholder that will work once the backend endpoint exists" |
| Magic multipliers | `performance/page.tsx:232-235` | `* 0.11`, `* 0.26`, `* 0.45` — fabricated, not computed |
| Trivial wrapper | `app/api/deps.py` | `yield from get_db()` adds zero value |

**Not slop (may look like it but isn't):**
- The 9 docs in `docs/agents/` — each serves a distinct purpose for a real agent system
- The 55 agent tools — each has real implementation and is used by the agent
- The `skills/` SKILL.md files — consumed by agent routing, not decorative
- SOUL.md and IDENTITY.md — runtime assets consumed by `app/agent/prompts.py`

---

## 13. Theoretical Correctness Audit

### Verified as Correct

- **All 22 routers mounted** in `app/api/router.py` and included in `app/main.py`
- **Full pipeline chain connected** from lead through draft generation, both HIGH and non-HIGH paths
- **All Celery tasks registered** with matching route keys in task routing map
- **Beat schedule** references correctly registered tasks
- **Agent loop terminates** (MAX_TOOL_LOOPS=5, history limit 50)
- **All settings toggles have real behavioral effects** (reviewer_enabled checked in review_tasks, auto_classify in classification, etc.)
- **Model evolution matches migration chain** (enum additions, column additions)

### Verified as Broken

- **B3: `is_suppressed` AND vs OR** — suppression check fails when both email and domain provided but only one is suppressed
- **M1: Pydantic schema gap** — `runtime_mode` and `pricing_matrix` silently stripped from API responses
- **F1: Dynamic Tailwind classes** — production CSS will not include dynamically interpolated color classes

### Suspicious But Not Provably Broken

- **B5: Cross-channel conversation routing** — intentional design but will break with multiple WhatsApp users
- **B9: Pipeline orphan risk** — if a chained step fails, PipelineRun stays "running" forever
- **F5: Stale hook closure** — currently masked because callers pass stable lambdas, but `refresh()` with changed params will use stale fetcher

---

## 14. Maintainability Audit

### Strengths

- **Backend module boundaries are clean.** Services contain business logic, routers are thin, workers handle async dispatch. Easy to find where something lives.
- **Prompt registry centralizes LLM interaction.** Adding a new prompt is a well-defined pattern.
- **Conventional commits** make git history navigable.
- **Architecture documentation is honest** — audit.md and refactor-roadmap.md give a new developer a true picture.

### Weaknesses

- **Frontend copy-paste debt.** F3 and F4 mean bug fixes must be applied in 2+ places.
- **Implicit pipeline coupling.** Each step calls the next via `.delay()` with no central orchestrator tracking progress.
- **No frontend component tests.** Changing a component has no automated safety net.
- ~~**SQLite test gap.**~~ **RESOLVED:** Tests run on PostgreSQL via testcontainers.

### Cost of Change

| Change Type | Cost | Why |
|-------------|------|-----|
| Add a new API endpoint | **Low** | Router pattern is clear, schema/service/router separation works |
| Add a new agent tool | **Low** | Tool registry pattern is well-defined |
| Add a new LLM prompt | **Low** | Prompt registry with typed definitions |
| Change DB schema | **Medium-High** | Must write migration + manually verify on Postgres |
| Change pipeline flow | **Medium** | Implicit `.delay()` chaining, no central orchestration map |
| Change frontend component | **Medium-High** | No tests, copy-paste means checking multiple files |
| Add API authentication | **High** | Every endpoint needs updating, no test infrastructure exists |

---

## 15. Runtime Risk Audit

### Inspires Confidence

- **LLM invocation tracking** — every call logged with full context. Debugging is possible.
- **Idempotency guards** — pipeline steps won't re-process already-handled leads.
- **Retry with backoff** — Celery tasks retry on failure with exponential backoff.
- **Task stop signals** — batch operations can be gracefully stopped via Redis.
- **Rate limiting on mail** — max 3 failed sends before 5-min cooldown.
- **Suppression checking** — outreach respects email/domain/phone suppression lists.
- **Reviewer feedback loop** — corrections aggregated weekly for prompt improvement.

### Does Not Inspire Confidence

- **Channel router threading (B1)** — unbounded thread creation per message under load.
- **Pipeline orphans (B9)** — if chaining fails, PipelineRun stuck in "running" with no detection.
- **Export OOM risk (B13)** — `query.all()` loads entire result set into memory.
- **Map page performance (F2)** — unbounded pagination loop through all leads.
- ~~**SQLite test gap (T1)**~~ **RESOLVED** — tests now run on PostgreSQL matching production.

---

## 16. What Is Excellent

1. **LLM observability system** — full invocation tracking, structured output with fallback chain, prompt versioning, role-based routing. Production-grade.
2. **Prompt injection defense** — multi-layered, with sanitizer, message separation, `<external_data>` tags, and anti-injection preamble. Better than most production LLM systems.
3. **Security tests** — 7 attack vectors verified. Not cosmetic.
4. **Architecture guardrail tests** — catch structural decay automatically. Rare in any codebase.
5. **Domain-specific business logic** — scoring, enrichment, and outreach reflect real Argentine market knowledge.
6. **Operational tooling** — init, up, down, export, import, preflight, seed, nuke. Full lifecycle scripted.
7. **Honest documentation** — architecture audit rates codebase 5.6/10. Security backlog lists unresolved HIGHs. Refactor roadmap says "don't do big-bang rewrites."
8. **Agent system** — sound loop with termination guarantee, tool registry with validation, channel routing, confirmation flow.
9. **Reviewer feedback loop** — structured corrections aggregated weekly for prompt improvement. This is a learning system.
10. **Conventional commits** — navigable git history with clear commit messages.

---

## 17. What Is Fragile

1. **Frontend dynamic Tailwind classes (F1)** — production styling silently broken.
2. **Pipeline chaining (B9)** — no orphan detection, no central orchestration.
3. **Map page performance (F2)** — unbounded data fetching.
4. ~~**SQLite-only tests (T1)**~~ **RESOLVED** — PostgreSQL via testcontainers.
5. **Channel router threading (B1)** — will break under concurrent WhatsApp/Telegram load.
6. **Suppression OR logic (B3)** — incorrect AND in query could allow outreach to suppressed contacts.
7. **Pydantic schema gap (M1)** — runtime mode panel silently shows nothing.
8. **SSE JSON parsing (F9)** — malformed event crashes chat streaming.
9. **Stale hook closure (F5)** — refresh with changed params uses stale fetcher.
10. **Export OOM (B13)** — large dataset export crashes the API process.

---

## 18. What Feels Inflated or Low-Signal

1. **`app/api/deps.py`** — single function that is `yield from get_db()`. Delete it.
2. **`security/page.tsx`** — ~70% copy of `notifications/page.tsx`. Extract shared component.
3. **Duplicate `STEP_CONFIG` and helpers** in `activity-pulse.tsx` vs `activity/page.tsx`. Extract to shared module.
4. **9 docs in `docs/agents/`** — each is useful today but high maintenance burden for a 4-agent system.
5. **Magic velocity multipliers** in `performance/page.tsx` — fabricated numbers, not computed from data.
6. **AI Health Card "placeholder" comment** — either the endpoint exists or it doesn't. Remove comment ambiguity.
7. **`__all__` exporting private functions** in `app/llm/client.py`.

---

## 19. Top 20 Findings

| Rank | ID | Severity | Type | Summary |
|------|----|----------|------|---------|
| 1 | T1 | ~~HIGH~~ RESOLVED | testing | ~~SQLite-only tests~~ Migrated to PostgreSQL |
| 2 | T2 | HIGH | testing | No Alembic migration tests |
| 3 | F1 | HIGH | correctness | Dynamic Tailwind classes broken in production |
| 4 | F2 | HIGH | runtime_risk | Unbounded map pagination loop |
| 5 | F3 | HIGH | ai_slop | Security/notifications pages 70% identical |
| 6 | B1 | HIGH | runtime_risk | Channel router creates thread pool per message |
| 7 | F4 | HIGH | ai_slop | Duplicate STEP_CONFIG/helpers across files |
| 8 | F5 | HIGH | correctness | Stale closure in usePageData hook |
| 9 | T3 | HIGH | security | No API authentication tests (no auth exists) |
| 10 | M1 | MEDIUM | correctness | Pydantic schema strips runtime_mode from responses |
| 11 | B3 | MEDIUM | correctness | Suppression check AND vs OR logic bug |
| 12 | B2 | MEDIUM | security | Crypto key derivation lacks proper KDF |
| 13 | B5 | MEDIUM | architecture | Cross-channel conversation routing too broad |
| 14 | F9 | MEDIUM | correctness | SSE JSON parse not wrapped in try/catch |
| 15 | T4 | MEDIUM | testing | No Celery/Redis integration tests |
| 16 | T5 | MEDIUM | testing | No frontend tests whatsoever |
| 17 | B9 | MEDIUM | runtime_risk | Pipeline failures silently orphan runs |
| 18 | F7 | MEDIUM | correctness | Leads page hard cap at 200 with no pagination |
| 19 | B4 | MEDIUM | correctness | Hardcoded model names in AI office status |
| 20 | D2 | MEDIUM | docs | 10 recommended ADRs not written |

---

## 20. Top 10 Quick Wins

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Replace dynamic Tailwind classes with lookup maps (F1) | 30 min | HIGH — fixes broken production styling |
| 2 | Add `runtime_mode` + `pricing_matrix` to Pydantic schema (M1) | 10 min | HIGH — fixes silent field stripping |
| 3 | Fix `is_suppressed` to use `or_()` (B3) | 5 min | HIGH — fixes correctness bug |
| 4 | Wrap SSE JSON.parse in try/catch (F9) | 5 min | MEDIUM — prevents chat crash |
| 5 | Extract shared NotificationListView from security + notifications (F3) | 1 hour | MEDIUM — removes 400 lines of duplication |
| 6 | Extract STEP_CONFIG to shared module (F4) | 30 min | MEDIUM — removes constant duplication |
| 7 | Fix trailing slash in briefs router (B8) | 2 min | LOW — fixes 307 redirects |
| 8 | Delete `app/api/deps.py`, import `get_db` directly (B12) | 10 min | LOW — removes trivial wrapper |
| 9 | Add `api_key` to log scrubber regex (B16) | 2 min | LOW — prevents plaintext API key logging |
| 10 | Fix `formatRelativeTime` for future dates (F20) | 2 min | LOW — prevents "Hace -3m" display |

---

## 21. Top 10 Hard Problems

| # | Problem | Effort | Why It's Hard |
|---|---------|--------|---------------|
| 1 | Migrate test suite to PostgreSQL (T1) | 2-3 days | Need Docker-based test infra, fixture migration, CI pipeline changes |
| 2 | Add API authentication (T3) | 3-5 days | Every endpoint needs updating, token management, middleware, tests |
| 3 | Add Alembic migration tests (T2) | 1-2 days | Need clean Postgres fixture, migration chain verification, CI integration |
| 4 | Rewrite channel router for proper async (B1) | 1-2 days | Must bridge sync agent loop with async Telegram/WhatsApp without creating threads |
| 5 | Add frontend testing infrastructure (T5) | 2-3 days | Need component test setup, mock API, CI integration, fixture patterns |
| 6 | Central pipeline orchestrator (B9) | 2-3 days | Replace implicit `.delay()` chaining with tracked orchestration |
| 7 | Add proper KDF to crypto module (B2) | 1 day | Need key migration for all existing encrypted values |
| 8 | Backend endpoint for geo leads (F2) | 1 day | Need new endpoint + migration for coordinate index + frontend refactor |
| 9 | Leads pagination (F7) | 1-2 days | Need pagination UI component + update all pages that fetch leads for name resolution |
| 10 | Write the 10 recommended ADRs (D2) | 3-5 days | Each requires research, decision documentation, stakeholder alignment |

---

## 22. What Should Be Refactored

1. **Frontend security/notifications pages** → Extract shared `NotificationListView` component
2. **Frontend activity constants/helpers** → Extract to `lib/task-utils.ts` + `components/shared/model-badge.tsx`
3. **`usePageData` hook** → Fix stale closure (add `fetcher` to deps or use ref pattern)
4. **Channel router** → Replace `asyncio.run` in running loop with proper coroutine forwarding
5. **Pipeline chaining** → Add pipeline health check for orphaned runs, consider central orchestration
6. **`app/api/deps.py`** → Delete, import `get_db` directly
7. **Lead name resolution** → Create lightweight `/leads/names` endpoint instead of fetching 200 full leads on every page
8. **Dynamic Tailwind classes** → Replace all template literals with complete class string lookup maps
9. **`_persist_invocation`** → Accept optional `db` parameter to reuse caller's session

---

## 23. What Should Not Be Touched

1. **`app/llm/` module** — The LLM layer is the crown jewel. Prompt injection defense, invocation tracking, structured output with fallback chain — don't refactor what's already excellent.
2. **`app/scoring/rules.py`** — Domain-specific scoring with real market knowledge. Don't "simplify" domain expertise.
3. **`app/agent/tool_registry.py`** — Hand-crafted for Hermes 3 format with parameter validation and type coercion. It works.
4. **Security tests (`test_security.py`)** — 7 real attack vectors tested. Don't reduce coverage.
5. **Architecture guardrail tests (`test_arch_guardrails.py`)** — Unique and valuable. Maintain and extend, don't refactor.
6. **`docs/architecture/audit.md`** — Honest self-assessment. Update it, don't replace it.
7. **`docs/plans/refactor-roadmap.md`** — Thoughtful incremental plan. Follow it, don't rewrite it.
8. **Agent tools (`app/agent/tools/`)** — 15 modules, 55 tools, all serving real purposes. No bloat to remove.
9. **SOUL.md / IDENTITY.md** — Runtime assets consumed by agent system. They're not decorative docs.
10. **`scripts/scouter.sh`** — Orchestrator that powers `make up/down/status/logs`. Works well.

---

## 24. Final Verdict

**This is a 7.5/10 codebase.** The backend is genuinely well-engineered (8/10) with excellent LLM observability and domain expertise. The frontend is functional but carries copy-paste debt and production styling bugs (6.5/10). Tests are substantive but blind to the most common production failure mode (6/10).

**What makes this codebase better than average:**
- The LLM layer is production-grade, not a prototype
- Security is taken seriously (prompt injection defense, encrypted secrets, transparent backlog)
- Documentation tells the truth instead of marketing the project
- Architecture shows cost awareness and operational experience
- AI slop is nearly absent — this is human-authored code

**What keeps it from being great:**
- ~~SQLite-only tests are a ticking time bomb~~ (Resolved: PostgreSQL via testcontainers)
- No API authentication is a known but unresolved gap
- Frontend copy-paste debt will diverge and create bugs
- Pipeline has no orphan detection
- Dynamic Tailwind classes are silently broken in production

**Recommendation:** Fix the 10 quick wins first (2-3 hours total). Then tackle the hard problems in priority order: Postgres test migration, API auth, channel router rewrite. The codebase has strong bones — the work is in closing the known gaps, not in architectural redesign.
