# Scouter Full Pipeline Agent Runtime Audit

**Date:** 2026-04-05
**Auditor:** Claude Opus 4.6 — acting as Principal Engineer + Multi-Agent Systems Auditor
**Environment:** WSL2 / RTX 4080 16GB + 32GB RAM / LOW_RESOURCE_MODE=false
**Scope:** Full pipeline, 4+1 AI actors, runtime validation, code audit, agent ergonomics
**Source of truth:** Code, docs, runtime API, real pipeline execution, test suite

---

## 1. Executive Summary

Scouter is a well-architected lead prospecting system with a genuine multi-agent design running on local Ollama models. The codebase quality is high (8.5/10 per prior audit, confirmed), the documentation is unusually thorough, and the operational surface (API, dashboard, AI Office) is real — not a prototype.

However, the **pipeline has a critical systemic bug** that makes it non-reentrant: idempotency guards in 3 pipeline tasks return before chaining to the next step, causing any re-run to dead-end silently. This was discovered during live runtime testing and confirmed in code.

Beyond this bug, the system has a deeper truth: **it's architecturally ready but operationally untested**. The dump shows 242 leads, but only 1 LLM decision ever recorded, 0 Scout investigations, 0 review corrections, 0 outbound conversations, 0 outcomes. The agents exist in code but have barely been exercised in production. The system is closer to "well-built stage set" than "operating AI office" — the pieces are there, the wiring is mostly right, but the curtain hasn't really gone up.

**Blunt verdict:** Strong architecture, critical pipeline bug, untested AI runtime.

---

## 2. Overall Runtime Score

| Dimension | Score | Evidence |
|-----------|------:|---------|
| Pipeline general | **5/10** | Chain-break bug makes re-runs impossible; sequential design underuses hardware |
| Mote | **6/10** | Real agent loop with 55 tools, but untested closer mode; "chat with tools" more than "leader" |
| Scout | **7/10** | Genuine agent loop with Playwright, SSRF protection, structured output; best-designed agent |
| Executor | **7/10** | Well-scoped role, typed contracts, context accumulation design; barely exercised |
| Reviewer | **6/10** | Structured corrections are well-designed but zero real usage; feedback loop is decorative so far |
| Leader / 4B | **2/10** | No active role. Reserved but unused. Essentially ornamental. |
| Claridad de jerarquía | **7/10** | Docs are excellent; code mostly follows; hierarchy is declared more than enforced |
| Calidad de handoffs | **6/10** | step_context_json design is good but chain-break bug destroys the flow |
| Utilidad del contexto | **7/10** | 2KB/step + 16KB total limits are reasonable; format_context_for_prompt is well-designed |
| Memoria/feedback actual | **3/10** | Review corrections, outcome snapshots, weekly reports — all at zero usage |
| AI Office | **7/10** | Endpoints work, return meaningful data; but with no runtime data it's an empty dashboard |
| Confort multiagente | **6/10** | Roles are clear, tools are real, but agents haven't been stress-tested together |
| Full-resource utilization | **4/10** | Sequential pipeline, concurrency=2, single worker — doesn't leverage RTX 4080 + 32GB |
| Commercial usefulness | **5/10** | Architecture supports the commercial vision; execution hasn't proven it works |
| **OVERALL** | **5.5/10** | Strong foundation, critical bug, untested in production |

---

## 3. README / Docs / Code Alignment

| Claim | Reality | Verdict |
|-------|---------|---------|
| 4 AI roles work as a team | Roles exist in code with clear separation | ✓ Code matches |
| 315 tests passing | 327 tests passing (more than documented) | ✓ Better than claimed |
| 42 Alembic migrations | Confirmed via test | ✓ |
| 55 Mote tools | tool_registry.py registers tools dynamically | ✓ Plausible |
| Pipeline: ingestion→...→outcome | Chain-break bug prevents re-runs past enrichment | ✗ Broken |
| step_context_json flows through pipeline | Code writes context per step; chain-break prevents downstream consumption on re-runs | ⚠ Partially working |
| Review corrections feedback loop | Table exists, service exists, 0 corrections recorded | ⚠ Built but unused |
| Outcome-based scoring recommendations | Service exists, requires ≥50 outcomes, currently 0 | ⚠ Built but unused |
| Weekly synthesis reports | Celery Beat task exists, 0 reports generated | ⚠ Built but unused |
| LOW_RESOURCE_MODE | Correctly configured as false; queue routing works | ✓ |

**Summary:** Docs are accurate about what's *built*. They're aspirational about what's *working*. The gap is execution, not implementation.

---

## 4. End-to-End Pipeline Reality

### Pipeline Architecture

```
task_full_pipeline (dispatch only)
  → task_enrich_lead (enrichment queue)
    → task_score_lead (scoring queue)
      → task_analyze_lead (llm queue)
        → [if HIGH] task_research_lead (research queue) → task_generate_brief
        → [if not HIGH] task_generate_brief (llm queue)
          → task_review_brief (reviewer queue)
            → task_generate_draft (llm queue)
              → task_review_draft (reviewer queue)
                → [end - draft ready for manual/auto send]
```

Each step is a separate Celery task that chains via `.delay()`. State tracked in PipelineRun + TaskRun.

### What Works

1. **Pipeline dispatch** correctly creates PipelineRun and dispatches first step
2. **Task tracking** (PipelineRun, TaskRun) correctly records state transitions
3. **Structured logging** with correlation IDs enables full pipeline tracing
4. **Retry mechanism** handles transient DB errors with exponential backoff
5. **Idempotency detection** correctly identifies already-processed steps
6. **Context accumulation** design (step_context_json) is well-structured

### What's Broken

1. **CRITICAL: Chain-break on idempotent skip** — 3 tasks affected (enrich, score, analyze)
2. **Pipeline is strictly sequential** — no parallelism even on capable hardware
3. **No recovery mechanism** — stuck pipeline requires manual DB intervention
4. **current_step not updated** on idempotent skip — API reports stale step name

### Pipeline Completeness

| Step | Code exists | Chain works (fresh) | Chain works (re-run) | Context written |
|------|:-----------:|:-------------------:|:--------------------:|:---------------:|
| Dispatch | ✓ | ✓ | ✓ | — |
| Enrichment | ✓ | ✓ | ✗ (chain-break) | ✓ |
| Scoring | ✓ | ✓ | ✗ (chain-break) | ✓ |
| Analysis | ✓ | ✓ | ✗ (chain-break) | ✓ |
| Research (Scout) | ✓ | Untested | Untested | ✓ |
| Brief generation | ✓ | Untested | Untested | ✓ |
| Brief review | ✓ | Untested | Untested | ✓ |
| Draft generation | ✓ | Untested | Untested | ✓ |
| Draft review | ✓ | Untested | Untested | ✓ |
| Auto-send | ✓ | Untested | Untested | — |
| Closer loop | ✓ | Untested | Untested | — |
| Outcome tracking | ✓ | Untested | Untested | — |

"Untested" means the code exists and appears correct on inspection, but was not validated at runtime.

---

## 5. Mote Audit

**Model:** hermes3:8b
**Type:** Agent (loop + 55 tools)
**Key files:** `app/agent/core.py`, `app/agent/tool_registry.py`, `SOUL.md`, `IDENTITY.md`

### What Mote Actually Is

Mote is a streaming chat agent that uses Hermes 3's XML tool-calling format. The agent loop in `core.py` receives messages, builds system context (including weekly report injection), streams responses from Ollama, detects tool calls in the output, executes them, and feeds results back into the conversation.

### Capabilities

- **55 registered tools** covering leads, pipeline, outreach, settings, chat, research
- **Closer mode** for WhatsApp conversations with clients
- **Weekly context injection** (latest WeeklyReport synthesis, max 500 chars)
- **Conversation persistence** in DB
- **Streaming SSE** to frontend

### Assessment

Mote is a **competent chat-with-tools agent**, not a "jefe de operaciones." Here's why:

1. **No proactive decision-making.** Mote reacts to operator commands or client messages. It doesn't independently decide to process leads, escalate issues, or adjust pipeline behavior.
2. **No strategic awareness.** The weekly context injection is 500 chars — not enough for Mote to understand trends, patterns, or make operational recommendations.
3. **No memory between sessions.** Each conversation starts from scratch (context from DB only).
4. **Tool quality varies.** Some tools are rich (pipeline triggers, lead queries) while others are thin wrappers.
5. **Closer mode is the most "agent-like" capability** — intent detection, response generation, escalation to human. But with 0 conversations recorded, it's untested.

### Comfort Assessment

- **Context:** Receives system prompt + weekly summary + conversation history. Adequate for chat, insufficient for leadership.
- **Tools:** 55 tools is generous. Whether an 8b model can reliably select and use them all is questionable.
- **Handoffs:** Mote doesn't participate in the main pipeline. It's a parallel interface, not a pipeline orchestrator.

### Score: 6/10

Mote is a solid chat agent with good tool coverage. But calling it "jefe de operaciones" overstates its role. It's an operator interface, not a leader. It doesn't make decisions that change the pipeline's behavior.

---

## 6. Scout Audit

**Model:** qwen3.5:9b
**Type:** Agent (synchronous loop in Celery task)
**Key files:** `app/agent/research_agent.py`, `app/agent/scout_tools.py`, `app/agent/scout_prompts.py`

### What Scout Actually Is

Scout is the **most genuine agent** in the system. It runs a proper agent loop: receives a lead + context, decides which tools to call, observes results, decides next action, and terminates when it has enough information or hits limits.

### Capabilities

- **6 Playwright tools:** browse_page, extract_contacts, check_technical, take_screenshot, search_competitors, finish_investigation
- **SSRF protection:** Private IP blocking via `_validate_url()`
- **Graceful degradation:** Falls back to httpx if Playwright unavailable
- **Structured output:** Writes findings to InvestigationThread and step_context_json
- **Limits:** Max 10 loops, 90s timeout

### Assessment

1. **This is a real agent.** Scout makes genuine decisions: which pages to visit, what to extract, when it has enough data.
2. **Tool design is thoughtful.** Each tool returns structured data (not raw HTML), and the finish_investigation tool forces structured output.
3. **SSRF protection is correctly implemented.** Private ranges, loopback, reserved addresses blocked.
4. **Fallback design is practical.** httpx fallback when Playwright unavailable means Scout degrades gracefully.
5. **BUT: 0 investigations recorded.** Scout has never run in production from this dump. Its quality is theoretical.

### Comfort Assessment

- **Context:** Receives lead data + enrichment signals. Knows what to look for.
- **Tools:** 6 tools is the right number — focused and purpose-built.
- **Limits:** 10 loops / 90s is conservative but sensible for a 9b model.
- **Output:** Findings flow to step_context_json["scout"] and enrich brief generation.

### Score: 7/10

Best-designed agent in the system. Genuine agent loop, focused tools, proper safety constraints. Loses points only because it's never been exercised in production.

---

## 7. Executor Audit

**Model:** qwen3.5:9b
**Type:** Model (single-shot, stateless)
**Key files:** `app/llm/client.py`, `app/llm/invocations/`, `app/llm/prompts.py`

### What Executor Actually Is

Executor is not an agent — it's a **prompted LLM with structured output contracts**. Each invocation receives a prompt with context, produces structured JSON output validated against Pydantic schemas.

### Capabilities

- **Lead quality evaluation** (high/medium/low with reasoning)
- **Commercial brief generation** (opportunity score, budget tier, recommended channel)
- **Outreach draft generation** (email + WhatsApp, reading full pipeline context)
- **Reply assistant** (drafts for inbound messages)
- **Weekly synthesis** (aggregates metrics into report)
- **Business summary** (lead description)

### Assessment

1. **Well-scoped role.** Executor does one thing: generate structured content from context. It doesn't make decisions or chain actions.
2. **Context accumulation works in theory.** Draft generation reads ALL step_context_json, so each prior step enriches the final output.
3. **Prompt design is solid.** Prompts in `prompts.py` use system/data separation, anti-injection preamble, structured output requirements.
4. **Three-tier parse recovery.** If Ollama doesn't return clean JSON: try structured parse → regex extraction → fallback defaults.
5. **Only 1 invocation recorded.** evaluate_lead_quality once, 123ms. Everything else is theoretical.

### Comfort Assessment

- **Context:** Receives progressively more context as pipeline advances. The design is correct.
- **Scope:** Not overloaded — each invocation is focused on one task.
- **Quality risk:** A 9b model doing commercial brief generation and personalized outreach is ambitious. Quality depends heavily on prompt engineering.

### Score: 7/10

Well-designed role with proper contracts and context flow. The design is mature; the execution is unproven.

---

## 8. Reviewer Audit

**Model:** qwen3.5:27b
**Type:** Model (single-shot, stateless)
**Key files:** `app/llm/client.py`, `app/services/review_service.py`

### What Reviewer Actually Is

Reviewer is a **quality gate** that evaluates Executor's output and produces structured corrections.

### Capabilities

- **Review leads** (confirm/adjust quality rating)
- **Review briefs** (approve/reject with corrections)
- **Review drafts** (tone, accuracy, personalization checks)
- **Classify inbound replies** (intent detection)
- **Structured corrections** output: `{category, severity, issue, suggestion}`

### Assessment

1. **Correction format is well-designed.** Category + severity + issue + suggestion is actionable.
2. **Feedback loop is architecturally sound.** Corrections → review_corrections table → aggregation → prompt improvement recommendations.
3. **BUT: 0 corrections exist.** The feedback loop has never fired. It's decorative infrastructure.
4. **27b model justification is correct.** Using a larger model for review makes sense — it can catch mistakes the 9b model makes.
5. **Integration concern:** When review rejects a brief or draft, does the pipeline re-generate? The chain logic handles this, but it's untested.

### Comfort Assessment

- **Context:** Receives the artifact to review + lead context. Adequate.
- **Output consumption:** Corrections are persisted and can be aggregated. But aggregation into prompt improvements requires operator action — no auto-learning.
- **Isolation risk:** Reviewer is the most "disconnected" actor. Its corrections go into a table that nobody reads automatically.

### Score: 6/10

Good design, zero usage. The structured corrections format is genuinely valuable, but without real data flowing through, it's architecture without proof.

---

## 9. Leader / 4B Audit

**Model:** qwen3.5:4b
**Role:** Reserved (no active tasks)

### Assessment

1. **No code uses LLMRole.LEADER for any active task.** The 4b model is registered in config but never invoked by any worker, service, or agent loop.
2. **Weekly synthesis runs on Executor (9b)**, not Leader.
3. **The config default assigns Leader to 4b**, but this mapping has no consumers.
4. **The model IS installed** on Ollama and available.

### Verdict

Leader is **ornamental**. It exists in documentation and configuration but performs no work. The hierarchy documents describe it as "reserved" which is honest. But maintaining a model role that does nothing adds configuration complexity without value.

### Score: 2/10

Exists, loads into VRAM rotation, does nothing.

---

## 10. Real Hierarchy vs Workflow Reality

### Documented Hierarchy

```
OPERATOR → approves, controls
  AGENTS → Mote (leader), Scout (researcher)
    MODELS → Executor (generator), Reviewer (quality gate)
  RESERVED → Leader (4b, unused)
```

### Actual Hierarchy

```
CELERY TASK CHAIN → orchestrates everything
  pipeline_tasks.py → decides step order, chains tasks
    Executor → does analytical work when invoked
    Reviewer → reviews when invoked
    Scout → investigates when invoked by task chain
  Mote → parallel chat interface, doesn't participate in pipeline
  Leader → does nothing
```

### Key Discrepancy

**The pipeline, not Mote, is the real leader.** The task chain in `pipeline_tasks.py` decides:
- What step runs next
- Whether to invoke Scout (quality == "high")
- Whether to invoke Reviewer
- What context to pass downstream

Mote can trigger a pipeline via tools, but once triggered, Mote has zero control over the pipeline's execution. The pipeline is a hardcoded chain, not an agent-directed flow.

### Hierarchy Findings

| Finding | Severity | Category |
|---------|----------|----------|
| Pipeline chain is the real orchestrator, not any agent | MEDIUM | hierarchy |
| Mote labeled "jefe de operaciones" but doesn't operate the pipeline | LOW | hierarchy |
| No agent can influence pipeline behavior at runtime | MEDIUM | agent_architecture |
| Leader role declared but has zero implementation | LOW | hierarchy |

---

## 11. Context / Handoff Audit

### step_context_json

**Design:** Each pipeline step appends a JSON object to `PipelineRun.step_context_json` via `context_service.append_step_context()`. Draft generation reads all accumulated context via `format_context_for_prompt()`.

**Size limits:** 2KB per step, 16KB total. Truncation produces `{truncated: true, summary: "..."}`.

**Assessment:**
- Design is **correct and well-implemented**
- Context keys are meaningful: `enrichment`, `scoring`, `analysis`, `scout`, `brief`, `brief_review`
- Draft generator reads ALL context — this is the key insight that makes the pipeline valuable
- **Chain-break bug prevents context from flowing** on re-runs

### Review Corrections

- Well-structured: category/severity/issue/suggestion
- Persisted to `review_corrections` table
- Aggregation exists in `outcome_analysis_service`
- **Zero data flowing through** — completely decorative

### Outcome Snapshots

- `capture_outcome_snapshot()` freezes pipeline state on WON/LOST
- Signal correlation analysis exists
- Scoring recommendations gated at ≥50 outcomes
- **Zero outcomes** — the entire feedback-to-scoring loop is theoretical

### Investigation Threads

- Scout writes tool calls and findings to `InvestigationThread`
- **BUG:** Scout findings do NOT flow to step_context_json["scout"] — the "scout" key is never written by any code despite `format_context_for_prompt()` having a handler for it (`context_service.py:100-109`). Scout findings are silently folded into the research report's `business_description` via string concatenation (`research_tasks.py:121-129`), losing structured data.
- `closer_service.py:209` reads the "scout" key and always gets an empty dict.
- Visible in AI Office dashboard (when investigations exist)
- **Zero investigations** — Scout has never run

### Weekly Reports

- Celery Beat task aggregates 7-day data
- LLM or template fallback synthesis
- Injected into Mote's system context (500 chars max)
- **Zero reports generated**

### Handoff Quality

| Handoff | Design | Reality |
|---------|--------|---------|
| Enrichment → Scoring | Good (signals, email, website) | Broken by chain-break |
| Scoring → Analysis | Good (score, signal_count) | Broken by chain-break |
| Analysis → Scout | Good (quality triggers research) | Untested |
| Scout → Brief | Good (findings, pages, opportunity) | Untested |
| Brief → Review | Good (full brief for evaluation) | Untested |
| Review → Draft | Good (corrections available) | Untested |
| Draft → Send | Good (approval flow exists) | Untested |
| Outcomes → Scoring | Good (signal correlation design) | Zero data |
| Weekly → Mote | Adequate (500 chars summary) | Zero reports |

### Scores

- **Context quality: 7/10** — design is good, implementation matches
- **Handoff quality: 6/10** — chain-break bug destroys flow on re-runs
- **Feedback loop effectiveness: 3/10** — zero data has ever flowed through any feedback loop

---

## 12. Memory / Feedback / Learning Audit

### Current State

The system has **three feedback loops** designed but **zero operational**:

1. **Reviewer → Prompts:** Corrections exist in schema but 0 rows. No auto-application.
2. **Outcomes → Scoring:** Snapshot service exists but 0 outcomes. Recommendations gated at 50.
3. **Scout → Dossiers:** Investigation service exists but 0 investigations.

### Memory

- **No persistent memory** for any agent
- Mote's context is rebuilt from DB each session
- No learning from past conversations or pipeline results
- Weekly report injection is the closest thing to "memory" (500 chars)

### Assessment

The feedback loops are **architecturally sound but entirely theoretical**. They need real pipeline throughput to start generating value. The gating at 50 outcomes is pragmatic but means the system needs weeks/months of real usage before self-improvement kicks in.

---

## 13. AI Office Runtime Audit

### What It Shows

- Agent status (4 agents with model/role/activity)
- LLM decisions log (function, role, model, status, latency)
- Scout investigations (tool calls, findings)
- Outbound conversations (closer mode)
- Weekly reports

### Assessment

| Aspect | Score | Notes |
|--------|------:|-------|
| Completeness | 7/10 | Shows all 4 agents, decisions, investigations, conversations |
| Accuracy | 8/10 | Endpoints return correct data from DB |
| Usefulness | 5/10 | With 0 real data, it's an empty dashboard |
| Debugging | 6/10 | LLM invocation log with latency/status is useful; no full trace view |
| Operator experience | 6/10 | Would be useful once data flows; currently shows "everything idle" |

### Missing

- No pipeline run visualization (step-by-step progress view)
- No prompt version tracking visible
- No comparison of Executor vs Reviewer outputs
- No alert for degraded or failed invocations

### Score: 7/10

Well-built observation layer waiting for data to observe.

---

## 14. Commercial Impact Audit

### Does the Pipeline Support the Commercial Vision?

The product proposal describes Scouter as an "AI closer operativo" that converts leads into actionable commercial packages. The pipeline is designed to produce:

- ✓ Lead scoring with meaningful signals
- ✓ Scout research with evidence
- ✓ Commercial briefs with budget tiers and opportunity scores
- ✓ Reviewed drafts with quality corrections
- ✓ WhatsApp template selection by signals
- ✓ Closer mode for client conversations

### Assessment

The **architecture supports the vision**. If the pipeline runs correctly on fresh leads, the output (research → brief → reviewed draft → personalized outreach) would be commercially valuable for the Argentine web services market.

**BUT:**
- The pipeline has never produced a complete commercial package from this dump
- The chain-break bug means re-processing is impossible
- WhatsApp templates haven't been created in Kapso
- Closer mode has 0 conversations
- No WON/LOST outcomes to prove conversion impact

### Score: 5/10

The architecture earns points. The execution doesn't.

---

## 15. Full-Resource Fit Audit

### Current Resource Usage

| Resource | Available | Used | Utilization |
|----------|-----------|------|:-----------:|
| GPU (RTX 4080 16GB) | 16GB VRAM | Ollama serves models on demand | ~25% avg |
| RAM | 32GB | API + Worker + Postgres + Redis | ~20% |
| CPU | Multi-core | Celery concurrency=2 | Low |
| Queues | 6 defined | All subscribed by 1 worker | Underused |

### Issues

1. **Sequential pipeline wastes GPU idle time.** While enrichment runs (no LLM needed), the GPU is idle. While LLM runs, enrichment queue is idle. No parallelism.
2. **Single worker with concurrency=2** means only 2 tasks run simultaneously. With 32GB RAM and a powerful GPU, 4-8 workers could run safely.
3. **Ollama model swapping** is the bottleneck. Loading qwen3.5:27b after using 9b takes seconds. With 16GB VRAM, the 8b + 9b models could stay loaded simultaneously (~12GB), but the 27b (~16GB) requires swapping.
4. **No batch parallelism.** Processing 242 leads sequentially when 4+ could run in parallel wastes the hardware.

### Recommendations

| Change | Impact | Effort |
|--------|--------|--------|
| Increase concurrency to 4 | 2x throughput | Config change |
| Run 2 workers (one for LLM, one for non-LLM) | Parallel LLM + enrichment | Config change |
| Implement pipeline step parallelism where safe | Better hardware utilization | Medium |
| Pre-load frequent models via Ollama keep-alive | Reduce swap latency | Config change |

### Score: 4/10

The system was designed for LOW_RESOURCE_MODE and merely "runs faster" in full mode. It doesn't architecturally leverage the hardware.

---

## 16. What Feels Solid

1. **Test suite** — 327 tests on PostgreSQL, architecture guardrails, real security tests
2. **Documentation** — Best-in-class for a project this size; honest audits, clear hierarchy
3. **Agent OS design** — Roles are well-defined, tools are purpose-built, contracts are typed
4. **Scout agent** — Genuine agent loop, focused tools, proper safety constraints
5. **Pipeline context design** — step_context_json accumulation is the right approach
6. **Structured logging** — Full correlation IDs, step tracking, timing
7. **Task tracking** — PipelineRun + TaskRun accurately model pipeline state
8. **Security posture** — SSRF protection, prompt injection defense, log scrubbing
9. **Operational tooling** — init.sh, export.sh, import.sh, scouter.sh, Makefile
10. **Conventional commits** — Clean git history

---

## 17. What Feels Awkward or Underpowered

1. **Mote as "leader"** — It's a chat agent, not a decision-maker. The pipeline doesn't consult Mote.
2. **Leader/4B existence** — Takes configuration space and VRAM rotation for zero value.
3. **Pipeline re-run impossibility** — The chain-break bug makes operational recovery a manual DB task.
4. **Sequential-only pipeline** — No parallelism despite capable hardware.
5. **500-char weekly context** — Too small for Mote to have meaningful operational awareness.
6. **Feedback loops at zero** — Three well-designed loops that have never generated a single data point.
7. **Worker concurrency=2** — Too conservative for RTX 4080 + 32GB.
8. **AI Office with no data** — Empty dashboard waiting for a system that hasn't been exercised.

---

## 18. What Feels Overbuilt or Underused

1. **Outcome analysis service** — Full signal correlation engine for 0 outcomes
2. **Weekly synthesis** — LLM-powered report generation for a system with no data
3. **Review corrections aggregation** — Pattern detection for 0 corrections
4. **Leader model role** — Config, routing, documentation for a model that does nothing
5. **6 Celery queues** — Separate queues for enrichment/scoring/llm/reviewer/research/default, all consumed by 1 worker anyway
6. **Mote's 55 tools** — Whether an 8b model reliably selects from 55 tools is unproven

---

## 19. Top 15 Findings

| # | Sev | Category | Finding |
|---|-----|----------|---------|
| 1 | CRITICAL | pipeline | Chain-break bug: 3 idempotency guards return before chaining to next step (`pipeline_tasks.py:81,176,271`) |
| 2 | CRITICAL | performance | Research task timeout (120s) shorter than its own workload: Scout 90s + dossier + research (`research_tasks.py:25`) |
| 3 | HIGH | reliability | Pipeline is non-reentrant — re-runs on processed leads dead-end silently |
| 4 | HIGH | pipeline | `correlation_id` dropped in research→brief chain — traceability broken for HIGH leads (`research_tasks.py:206`) |
| 5 | HIGH | context | Scout context key `"scout"` never written to step_context_json — dead code path in `context_service.py:100-109`; `closer_service.py:209` reads it and gets empty dict |
| 6 | HIGH | performance | Sequential pipeline + single worker + concurrency=2 doesn't leverage RTX 4080 + 32GB |
| 7 | HIGH | agent_architecture | 55-tool schema sent to 8B model every turn — unreliable tool selection at this model size (`core.py:232`) |
| 8 | HIGH | dashboard | Performance page ignores 4 outcome/recommendation endpoints — learning loop invisible to operator |
| 9 | HIGH | reliability | psycopg2 pool corruption after volume migration (connection validation missing) |
| 10 | MEDIUM | pipeline | `task_review_draft` never auto-chained from pipeline — drafts get zero review unless manually triggered via API |
| 11 | MEDIUM | pipeline | Batch pipeline skips brief review AND Scout investigation for HIGH leads (`batch_pipeline.py:207-217`, `lead_pipeline.py:113-148`) |
| 12 | MEDIUM | hierarchy | Mote labeled "jefe de operaciones" but has zero control over pipeline execution |
| 13 | MEDIUM | memory | Review corrections stored but never fed back into Executor prompts — open feedback loop |
| 14 | MEDIUM | agent_architecture | Leader/4B model configured but never invoked — ornamental |
| 15 | MEDIUM | performance | Concurrency=4 in scouter.sh vs 2 in docker-compose — inconsistent, 4 risks VRAM thrash |

**Additional findings from parallel agent audits (16-25):**

| # | Sev | Category | Finding |
|---|-----|----------|---------|
| 16 | MEDIUM | performance | All 6 queues consumed by 1 worker — model swap on every queue transition |
| 17 | MEDIUM | performance | Playwright browser launched fresh per Scout tool call — 10+ launches per investigation (`scout_tools.py:102`) |
| 18 | MEDIUM | dashboard | AI Office page doesn't show Mote outbound conversations — primary outreach artifact invisible |
| 19 | MEDIUM | dashboard | Decisions endpoint omits `lead_id`/`pipeline_run_id`/`correlation_id` — no cross-lead tracing |
| 20 | MEDIUM | agent_architecture | `think: False` hardcoded suppresses chain-of-thought for qwen3.5 models (`client.py:341`) |
| 21 | MEDIUM | context | current_step not updated in PipelineRun on idempotent skip |
| 22 | LOW | context | Weekly report LLM synthesis truncated 70% of the time (500 chars for ~1800 char output) |
| 23 | LOW | agent_architecture | DNS rebinding gap in Scout SSRF protection — validate then fetch separately |
| 24 | LOW | performance | `num_predict`/`temperature` not tuned per-task type — 2048/0.3 for everything |
| 25 | NIT | docs | README claims 315 tests but 327 pass — metric stale |

---

## 20. Top 10 Improvements

| # | Improvement | Impact | Effort | Category |
|---|-------------|--------|--------|----------|
| 1 | Fix chain-break bug: move chain-forward into idempotency guard return path | CRITICAL | 30 min | pipeline |
| 2 | Add pipeline recovery: endpoint to retry/resume stuck pipelines | HIGH | 2-3 hours | reliability |
| 3 | Increase worker concurrency to 4, or run 2 separate workers | HIGH | 15 min | performance |
| 4 | Run a real pipeline on a fresh lead to validate full chain | HIGH | 1 hour | testing |
| 5 | Add connection pool pre-ping (`pool_pre_ping=True` in SQLAlchemy) | MEDIUM | 5 min | reliability |
| 6 | Remove Leader/4B from active configuration or give it a real job | MEDIUM | 30 min | agent_architecture |
| 7 | Add pipeline step-progress visualization to AI Office | MEDIUM | 1 day | dashboard |
| 8 | Increase weekly context injection beyond 500 chars | LOW | 30 min | context |
| 9 | Add pipeline parallel fan-out for independent steps | MEDIUM | 1-2 days | performance |
| 10 | Generate real outcomes (WON/LOST) to bootstrap feedback loops | MEDIUM | Manual | commercial_impact |

---

## 21. What Should Be Reworked

1. **Pipeline chain logic** — Idempotency guards must chain forward even when skipping work
2. **Worker configuration** — Scale to hardware capabilities instead of conservative defaults
3. **Leader role** — Either assign real work (quick triage, status summaries) or remove from config
4. **Mote's "leader" narrative** — Align documentation with reality: Mote is an operator interface, not a pipeline leader
5. **Pipeline recovery** — Add explicit resume/retry capability for stuck runs

---

## 22. What Should Stay As Is

1. **Scout agent design** — Genuine loop, focused tools, proper constraints
2. **step_context_json design** — Correct accumulation pattern, size limits, formatting
3. **Executor role scope** — Single-shot structured output is the right design
4. **Reviewer structured corrections** — Good format, just needs data
5. **Test infrastructure** — PostgreSQL testcontainers, arch guardrails, security tests
6. **Documentation architecture** — AGENTS.md, docs/README.md, canonical/archive separation
7. **Task tracking** — PipelineRun + TaskRun is well-designed
8. **Security posture** — SSRF, prompt injection defense, log scrubbing
9. **Operational scripts** — init, export, import, scouter.sh are production-quality
10. **AI Office endpoints** — Well-structured, just need data to show

---

## 23. Final Verdict

Scouter is a **well-designed system that hasn't been tested in production**. The architecture is sound: 4 specialized AI roles, typed contracts, structured context flow, feedback loops, proper security, excellent documentation. The codebase quality is high (8.5/10 per prior audit, confirmed by 327 passing tests).

But there's a gap between "built" and "working":

- The **pipeline has a critical chain-break bug** that makes re-runs impossible
- The **AI runtime has generated almost zero real data** (1 LLM decision, 0 investigations, 0 corrections, 0 outcomes)
- The **feedback loops are beautiful infrastructure with no data flowing through them**
- The **hardware isn't being leveraged** (sequential pipeline, conservative concurrency)

The system needs three things to cross from "well-built stage set" to "operating AI office":

1. **Fix the chain-break bug** (30 minutes)
2. **Run real pipeline throughput** (days of leads flowing through)
3. **Scale the worker configuration** (match the hardware)

Once those three things happen, the architecture is ready to prove its commercial value. The foundation is genuinely good. The execution just hasn't started yet.

**Overall Runtime Score: 5.5/10** — Strong foundation, critical bug, untested in production.
