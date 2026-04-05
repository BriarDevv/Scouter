# Scouter Full Pipeline Agent Improvement Plan

**Date:** 2026-04-05
**Source:** [scouter-full-pipeline-agent-runtime-audit.md](../audits/scouter-full-pipeline-agent-runtime-audit.md)
**Current score:** 5.5/10 → **Target: 8/10**

---

## Phase 0 — Fix Critical Pipeline Friction (1-2 hours)

The pipeline chain-break bug is the single highest-impact issue. Nothing else matters until this is fixed.

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 0.1 | Fix chain-break in `task_enrich_lead`: move `task_score_lead.delay()` into idempotency guard return path | CRITICAL | 10 min | `app/workers/pipeline_tasks.py:72-81` |
| 0.2 | Fix chain-break in `task_score_lead`: move `task_analyze_lead.delay()` into idempotency guard return path | CRITICAL | 10 min | `app/workers/pipeline_tasks.py:162-176` |
| 0.3 | Fix chain-break in `task_analyze_lead`: move research/brief chain into idempotency guard return path | CRITICAL | 15 min | `app/workers/pipeline_tasks.py:257-271` |
| 0.4 | Update `current_step` in PipelineRun when idempotency skip happens | MEDIUM | 15 min | `app/workers/pipeline_tasks.py` (3 locations) |
| 0.5 | Add `pool_pre_ping=True` to SQLAlchemy engine config | MEDIUM | 5 min | `app/core/database.py` or engine creation |
| 0.6 | Fix `correlation_id` dropped in research→brief chain | HIGH | 5 min | `app/workers/research_tasks.py:206` |
| 0.7 | Fix research task timeout: `soft_time_limit=120` → `300` | CRITICAL | 2 min | `app/workers/research_tasks.py:25` |
| 0.8 | Write Scout context to step_context_json: add `append_step_context(db, pipeline_uuid, "scout", {...})` | HIGH | 15 min | `app/workers/research_tasks.py` |
| 0.9 | Add test: pipeline re-run on already-enriched lead chains correctly | HIGH | 30 min | `tests/` |

**Definition of Done:** Pipeline re-run on an already-processed lead progresses through all steps without dead-ending. New test validates this.

**Expected score impact:** 5.5 → **7/10**

---

## Phase 1 — Strengthen Agent Roles and Handoffs (3-5 hours)

Align agent roles with reality and remove dead weight.

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 1.1 | Add pipeline recovery endpoint: `POST /pipelines/runs/{id}/resume` | HIGH | 2 hrs | `app/api/v1/pipelines.py`, new service |
| 1.2 | Remove Leader/4B from active config or assign real work (e.g., quick lead triage) | MEDIUM | 1 hr | `app/llm/catalog.py`, `app/core/config.py`, `.env.example` |
| 1.3 | Update Mote documentation: "operator interface" not "jefe de operaciones" | LOW | 30 min | `docs/agents/hierarchy.md`, `docs/agents/identities.md` |
| 1.4 | Add pipeline step notification to Mote context (so Mote knows what happened) | MEDIUM | 1 hr | `app/agent/core.py`, context building |
| 1.5 | Extract `_track_failure` helper duplication across 3 worker files | MEDIUM | 1 hr | `app/workers/_helpers.py` (new), 3 worker files |

**Definition of Done:** Stuck pipelines can be resumed via API. Leader role resolved. Mote documentation matches reality.

**Expected score impact:** 7 → **7.5/10**

---

## Phase 2 — Improve Context, Feedback, and Memory (1-2 days)

Make the feedback loops generate their first real data.

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 2.1 | Run full pipeline on 5-10 fresh leads (create via API + trigger pipeline) | HIGH | 2 hrs | Manual via API |
| 2.2 | Increase weekly context injection from 500 to 1500 chars | LOW | 15 min | `app/agent/core.py` |
| 2.3 | Add pipeline context summary to Mote's available tools (query step_context_json) | MEDIUM | 1 hr | `app/agent/tool_registry.py` |
| 2.4 | Trigger manual weekly report generation to bootstrap Mote context | MEDIUM | 15 min | `POST /ai-office/weekly-reports/generate` |
| 2.5 | Manually mark 5+ leads as WON/LOST to bootstrap outcome tracking | MEDIUM | 30 min | Via API/dashboard |
| 2.6 | Verify review corrections are actually generated during pipeline (brief review + draft review) | HIGH | 1 hr | Run pipeline, check DB |

**Definition of Done:** At least 1 complete pipeline run with all steps executed. At least 1 weekly report generated. At least 5 outcomes recorded. Review corrections table has real data.

**Expected score impact:** 7.5 → **8/10**

---

## Phase 3 — Improve AI Office and Operator Visibility (1-2 days)

Make the dashboard useful for daily operations.

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 3.1 | Add pipeline run step-by-step progress view to AI Office | MEDIUM | 1 day | Dashboard component + existing API |
| 3.2 | Add "last pipeline result" summary to lead detail page | MEDIUM | 2 hrs | Dashboard lead detail |
| 3.3 | Add alert/badge for degraded or failed LLM invocations | LOW | 2 hrs | Dashboard AI health card |
| 3.4 | Show Executor vs Reviewer output comparison for reviewed items | LOW | 3 hrs | Dashboard component |
| 3.5 | Add "retry failed pipeline" button to lead detail | MEDIUM | 2 hrs | Dashboard + API from Phase 1.1 |

**Definition of Done:** Operator can see pipeline progress step-by-step, retry failed pipelines from UI, and identify degraded AI invocations.

**Expected score impact:** 8 → **8.5/10**

---

## Phase 4 — Better Full-Resource Utilization (1 day)

Leverage the RTX 4080 + 32GB properly.

| # | Task | Sev | Effort | Files |
|---|------|-----|--------|-------|
| 4.1 | Increase Celery concurrency from 2 to 4 | HIGH | 5 min | `docker-compose.yml`, `scripts/scouter.sh` |
| 4.2 | Run 2 workers: one for LLM queues (llm, reviewer), one for rest | MEDIUM | 30 min | `scripts/scouter.sh`, `Makefile` |
| 4.3 | Configure Ollama keep-alive for frequently-used models (9b, 8b) | MEDIUM | 15 min | Ollama config or API call |
| 4.4 | Add batch pipeline parallelism: process N leads concurrently (default N=4) | MEDIUM | 4 hrs | `app/workers/pipeline_tasks.py` batch logic |
| 4.5 | Add performance metrics endpoint: pipeline throughput, avg step latency | LOW | 2 hrs | `app/api/v1/performance.py` |

**Definition of Done:** Worker processes 4+ tasks concurrently. Batch pipeline processes multiple leads in parallel. LLM model swap latency reduced.

**Expected score impact:** 8.5 → **9/10**

---

## Phase 5 — Long-Term Agent Maturation (ongoing)

Not urgent. Strategic improvements for when the system has real throughput.

| # | Task | Effort | Priority |
|---|------|--------|----------|
| 5.1 | Give Mote pipeline awareness: inject last 3 pipeline summaries into context | 2 hrs | P2 |
| 5.2 | Auto-apply top review corrections to prompts (with operator approval) | 1 day | P2 |
| 5.3 | Implement scoring weight auto-adjustment when outcome threshold met | 1 day | P3 |
| 5.4 | Add Scout memory: cache investigation findings per domain for reuse | 1 day | P3 |
| 5.5 | Evaluate whether Leader/4B should become a triage/routing agent | 2 hrs | P3 |
| 5.6 | Add Mote proactive alerts: "3 HIGH leads ready for review" | 4 hrs | P2 |
| 5.7 | Pipeline branching: allow parallel Scout + Brief for different lead segments | 2 days | P3 |

---

## Commit Strategy

All changes follow conventional commits (per AGENTS.md / ADR-003):

- `fix(pipeline): chain forward on idempotent skip in enrich/score/analyze tasks`
- `fix(db): add pool_pre_ping for connection validation`
- `test(pipeline): verify re-run chains correctly on processed leads`
- `feat(pipeline): add resume endpoint for stuck pipeline runs`
- `refactor(workers): extract shared _track_failure helper`
- `chore(config): resolve leader/4b role — remove or assign work`
- `docs(agents): align Mote documentation with actual role`
- `feat(dashboard): add pipeline step progress visualization`
- `perf(worker): increase concurrency and split LLM/non-LLM workers`

---

## PR Breakdown

| PR | Phase | Size | Risk |
|----|-------|------|------|
| Fix chain-break + pool_pre_ping + test | 0 | Small | Low |
| Pipeline recovery endpoint + worker helper extraction | 1 | Medium | Low |
| Leader role resolution + Mote docs update | 1 | Small | Low |
| Context/feedback bootstrapping (manual + code) | 2 | Small | Low |
| AI Office pipeline visualization | 3 | Medium | Low |
| Worker scaling + batch parallelism | 4 | Medium | Medium |

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Chain-break fix introduces new bugs | Existing 327 tests + new test specifically for re-run scenario |
| Increased concurrency causes resource contention | Monitor with `make status` and Celery flower |
| Pipeline resume endpoint allows inconsistent state | Validate pipeline state before resuming; only resume from known-stuck states |
| Model swap latency with more concurrent LLM tasks | Ollama keep-alive + limit concurrent reviewer invocations |
| Batch parallelism introduces race conditions | Each lead gets its own PipelineRun — no shared state between parallel runs |

---

## Definition of Done by Phase

| Phase | Criteria |
|-------|---------|
| 0 | Pipeline re-runs progress past enrichment/scoring/analysis; new test passes; `pytest -q` all green |
| 1 | Stuck pipelines resumable via API; Leader role resolved; Mote docs updated |
| 2 | ≥1 complete pipeline run with all steps; ≥1 weekly report; ≥5 outcomes; review corrections >0 |
| 3 | Pipeline progress visible in AI Office; retry button works; degraded invocations flagged |
| 4 | 4+ concurrent tasks; batch processes N leads in parallel; model swap latency <3s |
| 5 | Ongoing — measured by feedback loop throughput and Mote operational awareness |

---

## Expected Score Trajectory

| Phase | Score |
|-------|------:|
| Current | 5.5/10 |
| After Phase 0 | 7/10 |
| After Phase 1 | 7.5/10 |
| After Phase 2 | 8/10 |
| After Phase 3 | 8.5/10 |
| After Phase 4 | 9/10 |
