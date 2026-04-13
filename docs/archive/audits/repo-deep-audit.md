> **ARCHIVED:** This document has been superseded. See [architecture/audit.md](../../architecture/audit.md) for the current version.

# Scouter Repository Deep Audit

**Date:** 2026-04-07
**Auditor:** Claude Opus 4.6 (5-agent parallel audit)
**Scope:** Full repository -- backend, frontend, agent/LLM, data layer, tests, infrastructure
**Codebase:** Python 3.12 / FastAPI + Next.js 16 / SQLAlchemy 2 / Celery / Ollama LLMs

---

## Overall Score: 6.5 / 10

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Structure | 7 | Clean layering (api/services/models/workers/workflows/llm/agent). Explicit `__all__` exports. Some god files remain. |
| Backend | 6 | Solid service patterns (notification emitter, task tracking, outreach generator). 19 transaction discipline violations. Memory-hungry full-table loads. |
| Frontend | 5 | Excellent type safety. No data caching layer. 6 god components (400-550 LOC). 100% client-rendered. ~50 silent catch blocks. |
| Pipelines | 7 | Well-designed state machine (tracked_task_step). Chaining works. Redis connection-per-call. One 324-line god function. |
| Data Model | 6 | Good constraints (partial unique indexes). 3 missing FK indexes. 3 god models (Lead 27 cols, InboundMessage 30, OperationalSettings 40+). |
| Testing | 6 | 337 tests, strong guardrail/security/idempotency tests. 6 API modules with zero coverage. No pytest markers. No coverage reporting. |
| Docs | 8 | Excellent structure (AGENTS.md, docs/README.md, ADRs, agent identity cards, skills). |
| Maintainability | 6 | Conventional commits, guardrail tests, skills system. Offset by transaction ambiguity, legacy ORM split, duplicated code. |
| Correctness | 6 | Variable shadowing bug in crawler (live). Missing db.commit in patch_mail_credentials. History truncation keeps oldest not newest. Double pagination. |
| AI Slop | 8 | Very little slop. Most code is purposeful. Only 2 deletion candidates (deploy_config_service, tasks.py re-export shim). |

---

## What Was NOT Analyzed

- `alembic/versions/` migration SQL content (only env.py and migration-apply test verified)
- `dashboard/package-lock.json` dependency audit
- `docs/archive/` historical documents
- `.omc/` orchestration state files
- Runtime behavior under concurrent load (static analysis only)

---

## Findings by Severity

### CRITICAL (Fix Immediately)

#### C-1. Path Traversal in Storage Service
- **File:** `app/services/research/storage_service.py:30-48`
- **Functions:** `get_file()`, `delete_file()`
- **Issue:** `rel_path` is joined to `STORAGE_DIR` without sanitization. `../../etc/passwd` resolves outside the storage root.
- **Confidence:** HIGH | **Impact:** HIGH
- **Fix:** Add `resolved.resolve().relative_to(STORAGE_DIR.resolve())` guard before any I/O.

#### C-2. Mote Agent Tool Results Not Sanitized (Prompt Injection)
- **File:** `app/agent/hermes_format.py:97-122`
- **Issue:** When Mote's tool handlers return data from the database or external sources, that data is formatted via `format_tool_result` without any sanitization. A lead with a business_name containing injection text (crawled from a malicious Google Maps listing) flows directly into the LLM context. The Executor/Reviewer pipeline applies `sanitize_field` and `<external_data>` tags; the Mote agent layer does not.
- **Also:** `app/agent/prompts.py:14-18` -- Mote's system prompt uses its own `SECURITY_PREAMBLE` covering only API key disclosure, not the `<external_data>` tag defense used in `app/llm/prompts/system.py:3-10`.
- **Confidence:** HIGH | **Impact:** HIGH
- **Fix:** Apply `sanitize_data_block` to tool result content before formatting. Add anti-injection preamble variant to Mote's system prompt.

#### C-3. Variable Shadowing Bug in Google Maps Crawler
- **File:** `app/crawlers/google_maps_crawler.py:91` and `:138`
- **Issue:** Line 91: `location = f"{zone}, {city}"` (outer loop -- city string). Line 138: `location = place.get("location", {})` (inner loop -- shadows with a dict). After the inner loop, the outer loop's next iteration uses the dict at line 97: `f"{cat} en {'latitude': ..., 'longitude': ...}"`. Second+ category searches are corrupted.
- **Confidence:** HIGH | **Impact:** HIGH
- **Fix:** Rename inner variable to `coords` or `geo_location`.

#### C-4. Agent History Truncation Keeps Oldest, Drops Newest
- **File:** `app/agent/core.py:134-141`
- **Issue:** `_load_history` orders by `created_at ASC` with `LIMIT 50`. For conversations >50 messages, this keeps the OLDEST 50 and drops the most recent. The agent loses context of what just happened.
- **Confidence:** HIGH | **Impact:** HIGH
- **Fix:** Use `ORDER BY created_at DESC LIMIT 50` then reverse the list.

#### C-5. No Token Budget Management in Agent Loop
- **File:** `app/agent/core.py:278-284`
- **Issue:** System prompt + full tools schema (30+ tools) + personality files + up to 50 history messages are concatenated with no token counting. With `num_ctx: 16384`, this exceeds the context window. Ollama silently truncates from the beginning, losing the system prompt and tools schema.
- **Confidence:** HIGH | **Impact:** HIGH
- **Fix:** Implement token estimation and trim history from oldest end while always preserving the system prompt.

#### C-6. Missing db.commit() in patch_mail_credentials
- **File:** `app/api/v1/settings/credentials.py:37-43`
- **Issue:** Calls `update_credentials(db, updates)` and returns, but never calls `db.commit()`. Credential updates are silently lost. Compare with `patch_whatsapp_credentials` at `messaging.py:63` which commits.
- **Confidence:** HIGH | **Impact:** HIGH

---

### HIGH (Fix This Sprint)

#### H-1. Tool Call Regex Fails on Nested JSON
- **File:** `app/agent/hermes_format.py:43-46`
- **Issue:** `r"<tool_call>\s*(\{.*?\})\s*</tool_call>"` uses lazy `.*?`. For nested JSON like `{"name": "x", "arguments": {"key": "val"}}`, the lazy match terminates at the first `}`, producing invalid JSON. Tool calls silently fail.
- **Confidence:** HIGH | **Impact:** HIGH

#### H-2. N+1 Query in Batch Reviews List
- **File:** `app/api/v1/batch_reviews.py:22-38`
- **Issue:** Loads all `BatchReview` rows, then for each accesses `r.proposals` triggering a lazy load per row. 50 batch reviews = 50 extra SELECT queries.
- **Confidence:** HIGH | **Impact:** MEDIUM

#### H-3. N+1 Query in Chat Conversation Detail
- **File:** `app/api/v1/chat.py:65-99`
- **Issue:** Loads messages, then for each message accesses `msg.tool_calls` triggering lazy loads.
- **Confidence:** HIGH | **Impact:** MEDIUM

#### H-4. Dashboard _load_leads Loads Entire Lead Table into Memory
- **File:** `app/services/dashboard/dashboard_service.py:73-75`
- **Issue:** `select(Lead).options(joinedload(Lead.source))` with no WHERE clause. All leads loaded into Python memory. Called by `get_dashboard_stats()` and `get_time_series()`. Will OOM at scale.
- **Confidence:** HIGH | **Impact:** HIGH

#### H-5. Missing FK Indexes on Hot Access Patterns
- **Files:**
  - `app/models/lead_signal.py:26-41` -- `lead_id` FK, no index (PostgreSQL FK doesn't auto-create index)
  - `app/models/artifact.py:22-36` -- `lead_id` FK, no index
  - `app/models/commercial_brief.py:77-80` -- `research_report_id` FK, no index
- **Confidence:** HIGH | **Impact:** MEDIUM

#### H-6. Flower (Celery Monitor) Exposed Without Authentication
- **File:** `docker-compose.yml:113-127`
- **Issue:** Flower on port 5555 with zero authentication. Exposes task arguments which may contain PII (lead emails, business names).
- **Confidence:** HIGH | **Impact:** HIGH

#### H-7. No Rate Limiting on Synchronous LLM Endpoints
- **File:** `app/core/config.py:125` -- `API_RATE_LIMIT` declared but never applied
- **Endpoints affected:** `POST /enrichment/{lead_id}`, `POST /scoring/{lead_id}`, `POST /outreach/{lead_id}/draft`, `POST /reviews/leads/{lead_id}`
- **Confidence:** HIGH | **Impact:** MEDIUM

#### H-8. Retry Decorator Retries on ALL Exceptions Including Parse Errors
- **File:** `app/llm/client.py:319-323`
- **Issue:** `@retry(stop=stop_after_attempt(...))` retries on ANY exception, including `LLMError("Empty response")`. An empty response is a model issue, not transient -- retrying wastes 3x latency.
- **Confidence:** HIGH | **Impact:** MEDIUM
- **Fix:** Add `retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError))`.

#### H-9. Classify Inbound Reply Has No Fallback -- Raises on LLM Failure
- **File:** `app/llm/invocations/reply.py:49-57`
- **Issue:** `classify_inbound_reply_structured` does not pass a `fallback_factory`. If LLM is unavailable, `result.parsed` is `None` and line 88 raises `LLMError`. All other invocations provide graceful fallbacks.
- **Confidence:** HIGH | **Impact:** MEDIUM

#### H-10. ~20 API Endpoints Return Raw Dicts Without response_model
- **Files:** `scoring.py:32,72,85`, `pipelines.py:161,207,213`, `batch_reviews.py:17,41`, `performance.py:41,80,100,109,117,135`, `ai_office.py:19,24,33,42,50`, `reviews.py:133`
- **Issue:** ~13% of endpoints bypass Pydantic validation. No OpenAPI docs generated. If a service accidentally includes sensitive data, Pydantic won't filter it.
- **Confidence:** HIGH | **Impact:** MEDIUM

---

### MEDIUM (Fix This Month)

#### M-1. Transaction Discipline Violations (19 Sites)
Services that call `db.commit()` instead of `db.flush()`:
- `enrichment_service.py:251`, `scoring_service.py:23`, `whatsapp_audit.py:22,35`, `telegram_audit.py:22,35`, `whatsapp_actions.py:128`, `context_service.py:57`, `outcome_tracking_service.py:90`, `reply_response_service.py:163,183`, `inbound_mail_service.py:309`, `outreach_service.py:80`, `closer_service.py:160`, `operational_task_service.py:356`
- **Impact:** Partial commits on failure leave inconsistent state
- **Root cause:** No enforced boundary. Convention is tribal knowledge.

#### M-2. Agent Tools Commit Independently (Non-atomic Turns)
- **Files:** `agent/tools/leads.py:301,384`, `territories.py:55,97,114`, `suppression.py:82,134`, `reviews.py:26,45`, `pipeline.py:34,76`, `crawl.py:66`, `settings.py:60`, `replies.py:41`
- **Issue:** Individual tool handlers call `db.commit()` while the agent loop at `core.py:406` also commits. If tool A commits but tool B fails, partial state persists.

#### M-3. Redis Connection-Per-Call in Operational Task Service
- **File:** `app/services/pipeline/operational_task_service.py:259,285,293`
- **Issue:** `Redis.from_url()` creates a new TCP connection per invocation. Under batch load (100 leads), 300+ ephemeral connections.
- **Fix:** Use module-level connection pool (like `whatsapp_actions.py:39-46` already does).

#### M-4. Telegram Dispatch Uses WhatsApp Setting Names
- **File:** `app/services/notifications/notification_service.py:302-306`
- **Issue:** Telegram dispatch reads `settings.whatsapp_min_severity` and `settings.whatsapp_categories`. Disabling WhatsApp categories silently suppresses Telegram notifications.

#### M-5. Frontend: 6 God Components (400-550 LOC)
- `app/leads/[id]/page.tsx` (550 lines, 18 useState hooks, duplicated refreshLeadContext)
- `app/responses/page.tsx` (~550 lines, eslint-disable)
- `app/outreach/page.tsx` (497 lines, useState ordering violation)
- `app/onboarding/page.tsx` (485 lines)
- `app/activity/page.tsx` (446 lines, 3s polling)
- `components/dashboard/control-center.tsx` (434 lines)

#### M-6. Frontend: No Data Caching Layer
- Every page independently fetches on mount. Navigating away and back triggers full re-fetch. No SWR, React Query, or custom cache. `lib/hooks/use-page-data.ts` exists but only `suppression/page.tsx` uses it.

#### M-7. Frontend: Silent Error Swallowing (~50 Catch Blocks)
- `lib/api/research.ts:12-14,26-28` -- `getLeadResearch` and `getCommercialBrief` catch ALL errors and return `null`. 401, 500, and timeouts all become "data doesn't exist."
- Most pages wrap fetches in `catch {}` labeled `// non-critical`.

#### M-8. Frontend: Uncoordinated Polling (5+ Intervals)
- Sidebar: 30s notification counts
- Activity-pulse: 4s active tasks
- System health: 30s
- Activity page: 3s task status
- AI office: 10s status
- No visibility pause, no error backoff, no deduplication.

#### M-9. SSRF DNS Rebinding Gap in Scout Tools
- **File:** `app/agent/scout_tools.py:46-74`
- **Issue:** `_validate_url` resolves hostname to check for private IPs, then returns original URL. The actual fetch happens later -- DNS could resolve to a different (private) IP between check and use.

#### M-10. Unbounded Export Query
- **File:** `app/api/v1/leads.py:63-92`
- **Issue:** `export_leads` uses `yield_per(100)` but the export functions likely materialize all results. With thousands of leads, OOM risk.

#### M-11. Territory Leads Loads All Then Slices in Python
- **File:** `app/api/v1/territories.py:80-81`
- **Issue:** `_get_leads_in_cities(db, territory.cities)` loads ALL leads, then `leads[:limit]`. LIMIT should be pushed to SQL.

#### M-12. Crypto Key Re-derived on Every Encrypt/Decrypt
- **File:** `app/core/crypto.py:30-39`
- **Issue:** 480,000 PBKDF2 iterations on every call. On hot paths (bulk credential reads), CPU bottleneck.
- **Fix:** Cache derived key at module load.

#### M-13. Scout Browser Launched Per Tool Call
- **File:** `app/agent/scout_tools.py:101-128`
- **Issue:** Full Chromium launch/close per page fetch. 5-8 tool calls per investigation = 5-8 browser launches (1-3s each).

#### M-14. Frontend: N+1 in Dossiers Page
- **File:** `dashboard/app/dossiers/page.tsx`
- **Issue:** Fetches all leads, then individually calls `getLeadResearch(lead.id)` for each. 50 leads = 51 HTTP requests.

#### M-15. Frontend: Double Pagination in Leads Table
- **File:** `dashboard/components/leads/leads-table.tsx`
- **Issue:** Parent page fetches server-paginated results (25 leads). LeadsTable applies its own client-side pagination on top, showing a subset of already-paginated results.

---

### LOW (Backlog)

| ID | Finding | File | Impact |
|----|---------|------|--------|
| L-1 | Deprecated `asyncio.get_event_loop()` creates unbounded threads | `agent/channel_router.py:111-121` | Thread leak under load |
| L-2 | Cross-conversation sync is overly broad (non-web channels share state) | `agent/channel_router.py:50-57` | Multi-tenant risk |
| L-3 | `format_signals` assumes ORM objects, crashes on plain strings | `llm/invocations/support.py:4-7` | AttributeError |
| L-4 | Hardcoded Argentina bounding box in map view | `dashboard/lib/api/leads.ts:112-114` | Geo lock-in |
| L-5 | ReadinessGate fires on every navigation | `dashboard/components/layout/readiness-gate.tsx:43` | Wasted API calls |
| L-6 | Zero code splitting (except map); Recharts ~200KB on every load | `dashboard/app/performance/page.tsx` | Bundle bloat |
| L-7 | Webhook secret returned in response body | `api/v1/settings/messaging.py:148` | Secret in logs |
| L-8 | GET endpoints that commit (get_or_create side effects) | `api/v1/settings/messaging.py:53,77` | Write on read |
| L-9 | Suppression model allows duplicate domain/phone entries | `models/suppression.py:14-15` | Data quality |
| L-10 | WhatsApp/Telegram credential schemas can't clear fields via null | `schemas/whatsapp.py:28`, `schemas/telegram.py:28` | UX bug |
| L-11 | `export_service.py` accepts unused `db` parameter | `services/research/export_service.py:15,55,80` | Dead code |
| L-12 | Instagram scraper: 2s sleep per profile, silent fail without Playwright | `crawlers/instagram_scraper.py:124,52-57` | Slow + silent |
| L-13 | Google scraping in search_competitors will be rate-limited | `agent/scout_tools.py:325-352` | Fragile |
| L-14 | Mixed Spanish/English in error messages and prompts | Systemic | i18n debt |
| L-15 | `tasks.py` backward-compat re-export shim (27 lines) | `workers/tasks.py` | Deletable |
| L-16 | `deploy_config_service.py` (23 lines) inlineable | `services/deploy_config_service.py` | Deletable |
| L-17 | DB query at Celery import time | `workers/celery_app.py:30-50` | Startup fragility |
| L-18 | Legacy `db.query()` in 6 files vs modern `select()` | Systemic | SQLAlchemy 2.0 debt |
| L-19 | No URL validation on LeadCreate schema | `schemas/lead.py:17-18` | Data quality |
| L-20 | Hardcoded tool count assertion in test | `tests/test_agent_core.py:14` | Brittle test |

---

## Systemic Patterns

### SYSTEMIC-1: Transaction Boundary Ambiguity
**Scope:** 19 service files + 8 agent tool files
**Pattern:** No enforced rule about who owns `db.commit()`. Some services commit, some flush, some do both. This creates partial commit risks and double-commit behavior.
**Root cause:** Tribal knowledge, no linter rule or base class enforcement.

### SYSTEMIC-2: Executor/Reviewer Pipeline vs Agent Layer Asymmetry
**Scope:** `app/llm/` (sanitized) vs `app/agent/` (unsanitized)
**Pattern:** The LLM invocation layer sanitizes inputs, wraps external data in tags, includes anti-injection preambles, and uses structured output validation. The Mote agent layer passes tool results raw, has no token management, and uses a simple regex parser.

### SYSTEMIC-3: Frontend Fetch-Render Boilerplate
**Scope:** ~19 page components
**Pattern:** Every page independently implements `useState(null) + useState(true) + useEffect(() => { fetch(); setData(); setLoading(false); }, [])`. A shared hook (`use-page-data.ts`) exists but is adopted in only 1 of 19 pages.

### SYSTEMIC-4: Silent Error Swallowing
**Scope:** ~50 catch blocks in frontend, ~10 in backend
**Pattern:** Errors caught and discarded with no logging, no user feedback, no metrics. Read failures become "empty" states.

### SYSTEMIC-5: Memory-Hungry Full-Table Loads
**Scope:** `dashboard_service.py`, `outcome_analysis_service.py`, `leader_service.py`
**Pattern:** Load entire tables into Python memory, aggregate in Python. Works at current scale (~1k leads) but will OOM at 10k+.

---

## End-to-End Flow Verification

| Flow | Status | Evidence |
|------|--------|----------|
| Lead ingestion (crawl -> create -> score -> enrich) | **Solid** | Tested in `test_outreach_workflow.py`, `test_scoring.py`. Idempotent dedup via `_compute_dedup_hash`. |
| Pipeline (research -> review -> outreach -> send) | **Solid** | `tracked_task_step` context manager provides clean state machine. Tested in `test_batch_workflow.py`, `test_operational_state.py`. |
| Inbound mail classification -> reply draft | **Fragile** | Classification has no fallback (C-9). Thread context builder is duplicated across generation and review (F-16). |
| Agent conversation (Mote chat -> tool calls -> response) | **Fragile** | History truncation drops recent messages (C-4). No token budget (C-5). Regex fails on nested JSON (H-1). Tool results unsanitized (C-2). |
| Google Maps crawl -> lead creation | **Broken** | Variable shadowing corrupts search query for 2nd+ category (C-3). |
| Dashboard aggregations | **Fragile** | Full-table loads (H-4). Will OOM at scale. |
| Outreach generation -> validation -> send | **Solid** | Post-validation pipeline (URL fabrication detection, word limits, brand leak) is well-implemented. |
| Notification dispatch (email + Telegram + WhatsApp) | **Fragile** | Telegram uses WhatsApp severity/category settings (M-4). |

---

## Kill List (Deletable)

| File | Reason |
|------|--------|
| `app/workers/tasks.py` | 27-line re-export shim. Update callers to import from `pipeline_tasks` directly. |
| `app/services/deploy_config_service.py` | 23-line read-only wrapper. Inline into single caller. |

---

## Preserve List (Strong Modules)

| Module | File | Why |
|--------|------|-----|
| Notification emitter | `services/notifications/notification_emitter.py` | Clean fire-and-forget with dedup, structured logging. 312 lines of solid event-driven code. |
| Outreach generator + validation | `services/outreach/generator.py` | Post-validation pipeline (URL fabrication, word limits, brand leak). 219 lines. |
| Task tracking state machine | `services/pipeline/task_tracking_service.py` | `tracked_task_step` context manager used consistently across all workers. |
| Structured invocation system | `llm/client.py:invoke_structured` | 4-tier fallback (direct parse -> markdown extract -> brace extract -> factory). Full observability per invocation. |
| LLM sanitizer | `llm/sanitizer.py` | Effective anti-injection defense for Executor/Reviewer pipeline. |
| Prompt registry | `llm/prompt_registry.py` | Type-safe prompt-to-schema binding. |
| Tool registry | `agent/tool_registry.py` | Clean registration with validation and schema generation. |
| Architecture guardrail tests | `tests/test_arch_guardrails.py` | 14 tests enforcing dependency direction, cross-domain imports, migration integrity. Rare and valuable. |
| Security test suite | `tests/test_security.py` + `tests/test_sanitizer.py` | 16 tests for prompt injection, secret exfiltration, tool abuse. |
| Scoring engine | `scoring/rules.py` | Clean, testable, override support from DB. |
| API proxy | `dashboard/app/api/proxy/[...path]/route.ts` | Path allowlist, traversal blocking, header sanitization. Well-engineered. |
| Type system | `dashboard/types/*` (12 files) | Comprehensive, zero `any`, proper generics. |
| API client | `dashboard/lib/api/client.ts` | Clean generic `apiFetch<T>`, retry logic, domain module separation. |
| Logging | `app/core/logging.py` | Clean structlog setup with sensitive key scrubbing. |
| Auth middleware | `app/api/auth.py` | Constant-time comparison, proper path exclusion. |

---

## Test Coverage Gaps

### API Modules With Zero Dedicated Tests

| Module | Endpoints | Priority |
|--------|-----------|----------|
| `territories.py` | 6 endpoints | HIGH |
| `batch_reviews.py` | 6 endpoints | HIGH |
| `settings/credentials.py` | 5 endpoints | HIGH |
| `settings/messaging.py` | 7 endpoints | HIGH |
| `performance.py` | 6 untested of 9 | HIGH |
| `telegram.py` | 1 webhook | MEDIUM |
| `whatsapp.py` | 2 webhooks | MEDIUM |
| `suppression.py` | 3 endpoints (service-only tests exist) | MEDIUM |

### Infrastructure With Zero Tests

| Area | Files | Priority |
|------|-------|----------|
| Scripts | `browserctl.py` (587 lines), `scouterctl.py`, `preflight.py`, `seed.py`, `mailctl.py` | MEDIUM |
| Frontend components | All components (0 unit tests beyond vitest config) | LOW |

### CI Gaps

- No `ruff format --check` (formatting drift undetected)
- No `mypy` (despite `strict = true` in pyproject.toml)
- No coverage reporting or threshold
- CI lint uses `--select F,W,I` (3 rules) vs pyproject.toml's 9 rule sets
- Duplicate PostgreSQL: CI service container unused (testcontainers overrides it)
- Redis CI service unused (Celery uses in-memory backend for tests)

---

## AI Slop Assessment

**Score: 8/10 -- Very little slop.**

The codebase is overwhelmingly purposeful. Findings:

| Pattern | Verdict | Evidence |
|---------|---------|----------|
| `deploy_config_service.py` (23 lines) | **SLOP** -- wrapper with no logic | Single caller could inline |
| `tasks.py` re-export shim (27 lines) | **SLOP** -- backward compat with no callers | Can delete |
| Error boundaries (16 identical copies) | **Borderline** -- should be a shared component | Reduces duplication but each is only 30 lines |
| `use-page-data.ts` hook adopted in 1/19 pages | **Justified but underadopted** -- the hook is well-designed | The 18 unadopted pages are the slop |
| Duplicated `_safe_rate`/`_build_thread_context` | **Justified duplication** -- would be premature to abstract at 2 copies | Monitor for 3rd copy |

---

## Infrastructure Findings

### Docker

| Finding | File | Impact |
|---------|------|--------|
| Source mount in containers (`- .:/app`) | `docker-compose.yml:58,109` | Mounts `.env`, `.git`, secrets into container. Dev-only, do not use in production. |
| `worker-llm` missing healthcheck | `docker-compose.yml:90-111` | Dead LLM worker undetected by orchestration. |
| Flower without authentication | `docker-compose.yml:113-127` | PII exposure via task arguments. |
| `NEXT_PUBLIC_API_URL` points to Docker hostname | `docker-compose.yml:136` | `http://api:8000` not resolvable by browser. |

### CI

| Finding | File | Impact |
|---------|------|--------|
| Lint rules narrower than pyproject.toml | `ci.yml:52` | E, N, UP, B, SIM, S violations pass CI silently. |
| No format check | `ci.yml` | Formatting drift. |
| No mypy | `ci.yml` | Type errors accumulate. |
| No coverage | `ci.yml` | No visibility into test coverage. |
| Unused services | `ci.yml:13-35` | PostgreSQL + Redis spin up but tests use testcontainers + in-memory. |

---

## References

All file paths are relative to repository root. Line numbers verified against commit `7a29e1d` (2026-04-07).
