# Scouter Operational Validation Audit

**Date:** 2026-04-05
**Auditor:** Claude Opus 4.6 — 3 parallel specialist agents + direct validation
**Environment:** WSL2 / RTX 4080 16GB + 32GB RAM / LOW_RESOURCE_MODE=false
**Scope:** Operational readiness, workflow determinism, automation reality, failure modes, operator clarity

---

## 1. Executive Summary

Scouter is architecturally complete but operationally immature. The pipeline from enrichment to draft generation is deterministic and automated. Batch review meetings, feedback loops, and improvement proposals are implemented. But **three blockers prevent real operation**:

1. **Batch review proposals have no dashboard UI.** The primary human-in-the-loop mechanism is only accessible via curl/API. The operator cannot see, evaluate, approve, or reject proposals from the dashboard.

2. **Approved proposals are a dead end.** `approve_proposal()` sets status="approved" but nothing transitions to "applied". The `applied_at` and `result_notes` fields exist in the model but no code writes to them. The learning loop breaks at the last mile.

3. **Research task silently drops non-completed leads.** If Scout/research returns a non-completed status, the pipeline task marks itself as succeeded but never chains to the next step. The PipelineRun stays "running" forever — a zombie.

Until these three are fixed, the system cannot operate autonomously. Everything else is polish.

---

## 2. System Readiness Score

| Dimension | Score | Evidence |
|-----------|------:|---------|
| Operational readiness | 5/10 | Pipeline works, batch reviews work, but no UI for proposals, no recovery for BatchReview stuck, research drops leads |
| Workflow determinism | 6/10 | Happy path deterministic, but HIGH-lead branch has silent drops, brief review doesn't gate on approval |
| Automation quality | 6/10 | Mid-pipeline excellent (enrich→draft), bookends manual (no crawl schedule, no WhatsApp webhook) |
| Operator clarity | 5/10 | Good health monitoring, good per-lead AI panel, but batch reviews invisible, no attention queue |
| Batch meeting usefulness | 6/10 | Threshold works (42 HIGH leads triggers), service complete, but proposals dead-end |
| Proposal usefulness | 3/10 | Schema + API exist, "approved" is terminal, never "applied" |
| Failure recovery | 4/10 | Resume endpoint covers main path, misses research branch and BatchReview |
| Observability for decisions | 6/10 | Decision log + investigation threads good, no error aggregation, no pipeline runs page |
| Real value measurement maturity | 3/10 | Metrics exist in backend endpoints, almost none have frontend or temporal tracking |
| Safe scalability | 5/10 | Runtime modes well-designed, closer mode non-functional (no webhook), no escalation path |

**Overall readiness: 5/10** — Strong foundation, three hard blockers.

---

## 3. Workflow Determinism Audit

### Status Transition Maps

**PipelineRun:** `queued → running → succeeded | failed`
**BatchReview:** `generating → reviewing → completed | failed`
**ImprovementProposal:** `pending → approved [DEAD END] | rejected [terminal]`
**OutreachDraft:** `PENDING_REVIEW → APPROVED → SENT | REJECTED`

### Dead-End States

| State | Model | Problem | Severity |
|-------|-------|---------|----------|
| ImprovementProposal "approved" | batch_review.py:58-59 | `applied_at` and `result_notes` never written by any code | CRITICAL |
| BatchReview "generating" | batch_review_service.py:196 | If LLM hangs or crashes, stays generating forever | HIGH |
| BatchReview "reviewing" | batch_review_service.py:228 | Same — no timeout, no cleanup | HIGH |
| PipelineRun "running" after research | research_tasks.py:169 | Research non-completed doesn't chain forward | CRITICAL |

### Ambiguous Decision Points

1. **Brief review doesn't gate draft generation** (`brief_tasks.py:200-207`): `task_generate_draft` chains regardless of reviewer approval. A rejected brief still gets a draft.
2. **Analysis branching reads DB directly** (`pipeline_tasks.py:335`): Uses `lead.llm_quality` from DB instead of the just-computed `analysis.quality`, creating a race window.
3. **Research task marks failure as success** (`research_tasks.py:169`): When report.status != "completed", `tracker.succeed(result)` is called with the failed status.

---

## 4. Automation Reality Audit

| Stage | Classification | Notes |
|-------|---------------|-------|
| Lead ingestion (crawl) | MANUAL | No schedule in Celery Beat |
| Lead ingestion (manual) | MANUAL | API only |
| Enrichment | FULLY AUTOMATED | Chains to scoring |
| Scoring | FULLY AUTOMATED | Chains to analysis |
| Analysis | FULLY AUTOMATED | Branches HIGH→research, other→draft |
| Scout research | FULLY AUTOMATED | Chains to brief (when successful) |
| Brief generation | FULLY AUTOMATED | Chains to brief review |
| Brief review | FULLY AUTOMATED | Chains to draft (regardless of approval) |
| Draft generation | FULLY AUTOMATED | Triggers batch review check |
| Draft approval | SEMI-AUTO | `require_approved_drafts` gates (default: True = manual) |
| Outreach send | SEMI-AUTO | Only in assisted/outreach/closer modes |
| Closer conversation | MANUAL | No inbound webhook — endpoint requires POST |
| Outcome tracking | SEMI-AUTO | Snapshot auto-fires on manual WON/LOST status change |
| Batch review | SEMI-AUTO | Auto-triggers on threshold, proposals require manual approval |
| Weekly reports | FULLY AUTOMATED | Celery Beat Sunday 20:00 |

**Bottom line:** Stages 3-9 are fully automated. Entry (crawl) and exit (send, closer) are manual. The closer mode is **non-functional in production** because nothing receives inbound WhatsApp messages.

---

## 5. Batch Review / Meetings Audit

### What Works
- Threshold check correctly detects 42 HIGH leads in real data
- `collect_batch_data()` gathers quality distribution, corrections, signals, outcomes, invocations
- Executor synthesis → Reviewer validation two-step pattern is implemented
- Error handling with status transitions (generating → failed on LLM error)
- Post-pipeline hook fires after every draft generation

### What Doesn't Work
- **Proposals are a dead end.** `approve_proposal()` at `batch_review_service.py:309-316` sets status="approved" and stops. No downstream action.
- **No dashboard UI.** Grep for `batch_review` and `batch-review` in dashboard directory returns zero matches.
- **No BatchReview recovery.** Stuck "generating"/"reviewing" reviews accumulate as zombies.
- **No proposal application mechanism.** Fields `applied_at` and `result_notes` are dead schema.

---

## 6. Proposal Lifecycle Audit

### Current Lifecycle
```
pending → approved [STOP — nothing happens]
        → rejected [terminal, correct]
```

### Required Lifecycle
```
pending → approved → applied (with result_notes) → measured
        → rejected [terminal]
```

### What's Missing
1. `apply_proposal()` function that executes the proposal (adjust scoring weight, modify prompt hint, etc.)
2. Transition from "approved" to "applied" with `applied_at` timestamp
3. `result_notes` populated after measuring impact
4. Dashboard UI for the complete lifecycle
5. Guardrail check after application (did metrics degrade?)

---

## 7. Failure-Mode Audit

| Failure | What Happens | Recovery | Severity |
|---------|-------------|----------|----------|
| Scout fails | Falls back to HTTP research | Automatic | LOW |
| Executor LLM fails | Pipeline marks step failed, no retry beyond Celery max_retries | Resume endpoint | MEDIUM |
| Reviewer LLM fails | Brief review skipped, draft generated anyway | Pipeline continues | LOW |
| Research returns non-completed | **Pipeline zombie — task succeeds but doesn't chain** | **None** | CRITICAL |
| Batch review Executor fails | BatchReview status="failed", executor_draft stores error | Manual re-trigger | MEDIUM |
| Batch review Reviewer fails | Falls back to Executor proposals | Automatic | LOW |
| BatchReview hangs mid-generation | **Zombie — stays "generating" forever** | **None** | HIGH |
| Proposal approved but never applied | **Dead end — nothing happens** | **None** | CRITICAL |
| Pipeline chain failure for HIGH leads | `task_analyze_lead` swallows error, lead abandoned | Manual resume (partial) | HIGH |
| Batch review check silently fails | bare `except: pass` — never detected | Threshold re-checks next pipeline | LOW |

### Silent Degradation Risks
- Research marking failures as successes (`tracker.succeed(result)` on non-completed)
- Brief review not gating on approval (rejected briefs still get drafts)
- Batch review check fire-and-forget with pass
- Proposal approval with no downstream effect

---

## 8. Operator Clarity Audit

### What the Operator CAN Do
- See infrastructure health (4 services with latency)
- Toggle runtime mode (safe/assisted/auto)
- Start/stop pipeline batch
- View agent status, decision log, investigations
- View per-lead AI reasoning (analysis, brief, review)
- View Mote conversations and weekly reports
- Trigger manual weekly report

### What the Operator CANNOT Do
- **See or manage batch review proposals** (no UI)
- **See pipeline run history** (no page)
- **Resume stuck pipelines from dashboard** (API only)
- **See what needs attention** (no attention queue, no badges)
- **Understand runtime mode differences** (no tooltips)
- **See aggregated errors** (no error summary view)
- **See queue depth or worker health beyond binary up/down**

### Operator Confidence Assessment
The operator can monitor the system but cannot manage the learning loop. The most important operational flow (batch review → propose → approve → apply → measure) is invisible to the dashboard.

---

## 9. AI Office Operational Audit

### Coverage: 60% of backend data surfaced

| Data | Backend | Dashboard |
|------|---------|-----------|
| Agent status | Yes | Yes |
| Decision log | Yes | Yes |
| Investigations | Yes | Yes |
| Conversations | Yes | Yes |
| Weekly reports | Yes | Yes |
| Batch reviews | Yes | **No** |
| Proposals | Yes | **No** |
| Pipeline runs | Yes | **No** |
| Error aggregation | No | No |
| Attention queue | No | No |

---

## 10. Real Value Metrics Audit

### Metrics That Exist in Code

| Metric | Backend | Frontend | Tracked Over Time |
|--------|---------|----------|-------------------|
| Approval rate | performance/ai-health | AI Performance tab | No (point-in-time) |
| Fallback rate | performance/ai-health | AI Performance tab | No |
| Correction patterns | reviews/corrections/summary | AI Performance tab | No |
| Signal correlations | performance/outcomes/signals | AI Performance tab | No |
| Win rate | performance/outcomes | AI Performance tab | No |
| Scoring recommendations | performance/recommendations | AI Performance tab | No |
| Batch review proposals | batch-reviews API | **None** | No |
| Pipeline throughput | pipelines/runs | **None** | No |

### Metrics That Don't Exist Yet

| Metric | Why It Matters |
|--------|---------------|
| Repeated correction rate (trending) | Measures if Executor is learning |
| Proposal hit rate | Measures if batch reviews are useful |
| Time-to-draft-usable | Measures operational efficiency |
| Manual edit rate | Measures automation quality |
| Pipeline completion rate | Measures reliability |
| Proposal application impact | Measures learning loop value |

---

## 11. What Real Growth Means in This System

Not vague words. Concrete, measurable things:

| Growth Indicator | How to Measure | Baseline | Target |
|-----------------|---------------|----------|--------|
| Executor learns from mistakes | Repeated correction categories decrease month-over-month | No data | -20% per month |
| Drafts get better | Approval rate without manual edits increases | No data | >70% |
| Proposals are useful | % of approved proposals with positive measured impact | 0% | >60% |
| Less human intervention | Drafts approved without edits / total drafts | No data | >50% |
| Better lead selection | Reply rate for HIGH leads improves | No data | +10-20% |
| System self-corrects | Scoring recommendations that match actual outcome patterns | 0 | >3 per batch review |
| Pipeline reliability | % of pipeline runs that complete without intervention | Unknown | >95% |
| Operator trust | Runtime mode advances from safe to assisted | safe | assisted within 2 months |

**Growth is NOT:** more features, more agents, more tools, more docs. Growth is these numbers moving in the right direction with evidence.

---

## 12. What Is Actually Automated

Enrichment → Scoring → Analysis → Research → Brief → Brief Review → Draft → Batch Review Check.

This chain fires automatically from a single pipeline trigger and produces a reviewed draft with a batch review threshold check at the end.

---

## 13. What Is Still Fragile

1. Research branch for HIGH leads — silent drop on failure
2. BatchReview stuck in generating/reviewing — no recovery
3. Pipeline resume doesn't cover all branches
4. Brief review doesn't gate draft generation
5. Proposal approval is a dead end
6. Closer mode requires manual POST — no webhook
7. No crawl schedule — pipeline sits idle

---

## 14. What Is Too Vague Today

1. "What should the operator approve?" — no context in dashboard
2. "What changed after applying a proposal?" — no measurement
3. "Is the system improving?" — no temporal metrics
4. "When should I move from safe to assisted?" — no checklist in UI
5. "Which proposals are high-value?" — evidence exists in API but not visible

---

## 15. What Must Be Made Explicit

1. Proposal lifecycle: pending → approved → applied → measured
2. Research failure handling: chain forward to brief/draft even on degraded research
3. Brief review gate: don't generate draft if brief rejected
4. BatchReview recovery: cleanup job or resume endpoint
5. Crawl schedule: add to Celery Beat
6. Scaling checklist: visible in dashboard, not just runbook

---

## 16. Top 15 Findings

| # | Sev | Category | Finding |
|---|-----|----------|---------|
| 1 | CRITICAL | dashboard | Batch review proposals have no UI — operator cannot approve/reject from dashboard |
| 2 | CRITICAL | workflow | `approve_proposal()` is terminal — "approved" never becomes "applied" |
| 3 | CRITICAL | pipeline | Research task silent drop — non-completed leads create zombie PipelineRuns |
| 4 | HIGH | recovery | Resume endpoint misses research/scout branch |
| 5 | HIGH | workflow | Brief review doesn't gate draft — rejected briefs still get drafts |
| 6 | HIGH | recovery | BatchReview stuck has no recovery mechanism |
| 7 | HIGH | automation | No crawl schedule — pipeline idle without human trigger |
| 8 | HIGH | automation | Closer mode non-functional — no WhatsApp inbound webhook |
| 9 | MEDIUM | dashboard | No attention queue — operator navigates blind |
| 10 | MEDIUM | dashboard | Pipeline runs page missing — no run history or error patterns |
| 11 | MEDIUM | workflow | `task_analyze_lead` swallows research chain failures |
| 12 | MEDIUM | metrics | No temporal metric tracking — can't measure growth |
| 13 | MEDIUM | dashboard | Runtime modes lack explanatory tooltips |
| 14 | LOW | code_quality | Status strings (not enums) for PipelineRun/BatchReview/Proposal |
| 15 | LOW | reliability | Batch review check fire-and-forget with bare except:pass |

---

## 17. Top 10 Improvements

| # | Improvement | Impact | Effort |
|---|-------------|--------|--------|
| 1 | Build batch review proposals UI in AI Office | CRITICAL | 1 day |
| 2 | Implement proposal applied state + `apply_proposal()` | CRITICAL | 2-3 hrs |
| 3 | Fix research task chain-forward on non-completed | CRITICAL | 30 min |
| 4 | Add BatchReview recovery (cleanup job or resume) | HIGH | 2 hrs |
| 5 | Fix brief review to gate draft generation on approval | HIGH | 30 min |
| 6 | Add pipeline runs page to dashboard | HIGH | 1 day |
| 7 | Add attention queue / operator inbox | MEDIUM | 1 day |
| 8 | Add crawl schedule to Celery Beat | MEDIUM | 30 min |
| 9 | Add resume support for research/scout branch | MEDIUM | 1 hr |
| 10 | Add temporal metric tracking (weekly snapshots) | MEDIUM | 3 hrs |

---

## 18. What Should Be Automated Next

1. **Crawl schedule** — daily or 2x/week territory crawl via Celery Beat
2. **Low-risk proposal auto-apply** — scoring weight adjustments with confidence=high AND impact=medium AND 50+ outcomes can auto-apply with guardrail check
3. **Draft auto-approval in assisted mode** — when Reviewer approves with high confidence, skip operator

---

## 19. What Should Not Be Automated Yet

1. **Proposal approval** — not enough outcome data to trust automatic decisions
2. **Outcome tracking** — WON/LOST requires human judgment
3. **Closer mode** — no inbound webhook means it can't function autonomously
4. **Channel switching** — "use WhatsApp instead of email" proposals need human validation
5. **Prompt modifications** — too high-risk for v1

---

## 20. Final Verdict

Scouter has built the right architecture. The pipeline, feedback loops, batch reviews, and proposals form a genuine learning system. But three hard blockers prevent it from operating:

1. The operator can't see proposals (no UI)
2. Approved proposals don't do anything (dead lifecycle)
3. Research failures create zombies (silent drop)

**Fix these three and the system score jumps from 5/10 to 7/10.** Add the pipeline runs page, attention queue, and temporal metrics and it reaches 8/10. That's when you can start moving from safe to assisted mode with confidence.

The system doesn't need more features. It needs the features it has to actually work end-to-end.
