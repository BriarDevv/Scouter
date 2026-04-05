# Scouter Full Pipeline Runtime Test Report

**Date:** 2026-04-05
**Environment:** WSL2 / Ubuntu, RTX 4080 16GB + 32GB RAM
**Auditor:** Claude Opus 4.6 (automated)

---

## 1. Environment Verification

| Check | Result |
|-------|--------|
| `LOW_RESOURCE_MODE` | `false` (confirmed in `.env`) |
| Python | 3.12.3 |
| Node | v20.20.1 |
| Docker | Running (Postgres 16 + Redis 7) |
| Ollama | Responding, 6 models loaded |
| API server | Started, healthy |
| Celery worker | Started, concurrency=2, prefork, 6 queues |

### Ollama Models Available

| Model | Present |
|-------|---------|
| hermes3:8b (Mote) | Yes |
| qwen3.5:4b (Leader) | Yes |
| qwen3.5:9b (Executor/Scout) | Yes |
| qwen3.5:27b (Reviewer) | Yes |
| qwen3:14b (extra) | Yes |
| qwen2.5:14b (extra) | Yes |

### Celery Queues Active

`default, enrichment, scoring, llm, reviewer, research` — all 6 queues subscribed by single worker with concurrency=2.

---

## 2. Health Check Results

```json
{
  "status": "ok",
  "components": [
    {"name": "database",  "status": "ok", "latency_ms": 1.83},
    {"name": "redis",     "status": "ok", "latency_ms": 2.22},
    {"name": "ollama",    "status": "ok", "latency_ms": 34.45},
    {"name": "celery",    "status": "ok"}
  ]
}
```

All 4 infrastructure components healthy.

---

## 3. Data State (from restored dump)

| Metric | Value |
|--------|-------|
| Total leads | 242 |
| Pipeline runs | 5 (2 succeeded, 3 failed) |
| LLM decisions recorded | 1 |
| Scout investigations | 0 |
| Review corrections | 0 |
| Outbound conversations | 0 |
| Weekly reports | 0 |
| Outcomes (WON/LOST) | 0/0 |
| Mote active conversations | 20 (from prior session) |

**Assessment:** The system has been barely exercised beyond initial enrichment/scoring. The AI pipeline (analysis, research, brief, review, draft, closer) has almost zero real usage data.

---

## 4. Test Suite Results

```
327 passed, 5 warnings in 70.58s
```

- All tests run on **PostgreSQL 16 via testcontainers** (not SQLite)
- 12 more tests than documented (327 vs 315)
- No failures
- Warnings: SECRET_KEY placeholder, Alembic path_separator deprecation

---

## 5. AI Office API Validation

### Agent Status Endpoint (`/ai-office/status`)

All 4 agents reported correctly:

| Agent | Status | Model | Extra |
|-------|--------|-------|-------|
| Mote | idle | hermes3:8b | 20 active conversations |
| Scout | idle | qwen3.5:9b | 0 investigations |
| Executor | idle | qwen3.5:9b | 0 invocations 24h |
| Reviewer | idle | qwen3.5:27b | 0% approval rate |

**Assessment:** Endpoint works and returns meaningful operational data. However, all agents are "idle" because the system hasn't been actively running pipeline work.

### Decisions Endpoint (`/ai-office/decisions`)

1 recorded decision:
- `evaluate_lead_quality` | executor | succeeded | 123ms

### Other Endpoints

| Endpoint | Status | Data |
|----------|--------|------|
| `/ai-office/investigations` | OK | 0 results |
| `/ai-office/conversations` | OK | 0 results |
| `/ai-office/weekly-reports` | OK | 0 results |
| `/performance/ai-health` | OK | 0 invocations, null latency |
| `/performance/outcomes` | OK | 0 WON, 0 LOST |
| `/reviews/corrections/summary` | OK | 0 patterns |

All endpoints respond correctly with empty/minimal data.

---

## 6. Full Pipeline Runtime Test

### Test Case: HIGH-score lead re-run

**Lead:** Peluqueria Estilo Sur (id: `15e1ddda...`)
**Score:** 82, **Quality:** high, **Status:** scored (already enriched)

### Trigger

```
POST /api/v1/scoring/{lead_id}/pipeline
→ 200 OK, task_id=ba323c56..., pipeline_run_id=a1241129..., status=queued
```

Pipeline dispatch worked correctly.

### Execution Timeline

| Time | Event | Result |
|------|-------|--------|
| T+0s | `task_full_pipeline` dispatched | OK, chains to `task_enrich_lead` |
| T+0.01s | `task_enrich_lead` starts | Runs on enrichment queue |
| T+0.02s | psycopg2 DatabaseError | Connection pool corruption from volume migration |
| T+0.03s | Retry scheduled | 30s countdown |
| T+30s | `task_enrich_lead` retry | Succeeds |
| T+30s | Idempotency: `already_enriched` | **Returns early — DOES NOT chain to scoring** |
| T+30s+ | **Pipeline stuck at "enrichment"** | No further activity |

### CRITICAL BUG: Pipeline Chain Break on Idempotent Skip

**Severity:** CRITICAL
**Category:** pipeline, reliability

The pipeline is **permanently stuck** at `status=running, current_step=enrichment`. The enrichment task succeeded but returned before reaching the `task_score_lead.delay()` chain call.

**Root cause:** In `app/workers/pipeline_tasks.py`, all 3 main pipeline tasks have idempotency guards that `return result` before the chain-to-next-step code:

| Task | Early return line | Chain line (never reached) |
|------|-------------------|---------------------------|
| `task_enrich_lead` | :81 | :105 (`task_score_lead.delay`) |
| `task_score_lead` | :176 | :198 (`task_analyze_lead.delay`) |
| `task_analyze_lead` | :271 | :302 (research/brief chain) |

**Impact:** Any pipeline re-run on a lead that has passed a step will dead-end. This makes the pipeline non-reentrant and non-recoverable without manual database intervention.

**Fix:** Move the chain-forward logic before or into the idempotency guard return path.

### Secondary Finding: psycopg2 Pool Corruption

**Severity:** MEDIUM
**Category:** reliability

The first enrichment attempt failed with `psycopg2.DatabaseError: error with status PGRES_TUPLES_OK and no message from the libpq`. This occurred because the PostgreSQL volume was migrated from the legacy ClawScout stack, leaving stale connection state. The retry mechanism handled it correctly (30s backoff), but this indicates the connection pool doesn't validate connections on checkout.

---

## 7. Performance Observations

### Startup Times

| Component | Time |
|-----------|------|
| API server (uvicorn) | ~5s |
| Celery worker | ~8s |
| First task dispatch | <1s |

### Ollama Latency

- Health check: 34ms
- The single recorded LLM invocation: 123ms (lead quality evaluation)
- No data on reviewer (27b) latency — never invoked in this session

### Queue Utilization

With concurrency=2 and 6 queues, the worker subscribes to all queues but can only process 2 tasks simultaneously. During the test, both workers were occupied (one for pipeline dispatch, one for enrichment), which is appropriate but leaves no headroom for concurrent pipeline runs.

---

## 8. Conclusions

### What Works

1. **API infrastructure** is solid — all health checks pass, endpoints respond correctly
2. **Task tracking** works well — PipelineRun and TaskRun accurately reflect state
3. **Structured logging** is excellent — full correlation IDs, step tracking, timing
4. **Retry mechanism** works — psycopg2 error recovered after 30s
5. **Idempotency detection** works — correctly identifies already-processed leads
6. **AI Office endpoints** return meaningful data even with minimal usage
7. **Test suite** is comprehensive and passing (327 tests on PostgreSQL)

### What Doesn't Work

1. **CRITICAL: Pipeline chain breaks on idempotent skip** — 3 tasks affected
2. **Pipeline is not reentrant** — cannot safely re-run on partially processed leads
3. **No runtime data** for most AI features — closer, weekly reports, outcomes, review corrections all at zero
4. **Connection pool** doesn't validate stale connections after infrastructure changes

### What Couldn't Be Validated

1. Full pipeline end-to-end (blocked by chain-break bug)
2. Scout/Playwright investigation quality
3. Executor analysis/brief/draft quality
4. Reviewer correction quality
5. Mote closer conversation quality
6. WhatsApp template flow (requires Kapso credentials)
7. Weekly synthesis generation

### Limitations of This Test

- Pipeline could not be tested beyond enrichment due to the chain-break bug
- No fresh leads were ingested (all 242 leads already enriched/scored)
- LLM inference quality was not tested (would require letting the pipeline run on a fresh lead)
- WhatsApp/email outreach was not tested (requires external credentials)
