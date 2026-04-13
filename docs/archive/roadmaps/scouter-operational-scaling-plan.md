> **ARCHIVED:** This document has been superseded. See [plans/refactor-roadmap.md](../../plans/refactor-roadmap.md) for the current version.

# Scouter Operational Scaling Plan

**Date:** 2026-04-05
**Source:** [scouter-operational-validation-audit.md](../audits/scouter-operational-validation-audit.md)
**Current score:** 5/10 → **Target: 8/10**

---

## Phase 0 — Eliminate the Three Blockers (1-2 days)

Nothing else matters until these are fixed. They are the difference between "demo" and "operable."

### 0.1 Batch Review Proposals UI (CRITICAL)

**What:** Dashboard page in AI Office to list batch reviews, view proposals, approve/reject.

**Files:** `dashboard/components/ai-office/batch-reviews-section.tsx` (new), `dashboard/app/ai-office/page.tsx` (wire), `dashboard/lib/api/client.ts` (add `getBatchReviews`, `getBatchReviewDetail`, `approveProposal`, `rejectProposal`)

**Shows:** Review list (date, trigger, batch size, proposals pending). Expandable detail with strategy brief, proposals table (category, description, impact, confidence, evidence, status). Approve/Reject buttons per proposal.

**Effort:** 1 day

### 0.2 Proposal Applied State + Lifecycle (CRITICAL)

**What:** Implement `apply_proposal()` that transitions approved → applied, sets `applied_at`, captures baseline metrics before application, and stores `result_notes` after measurement.

**Files:** `app/services/pipeline/batch_review_service.py` (add `apply_proposal()`), `app/api/v1/batch_reviews.py` (add `POST /proposals/{id}/apply`), dashboard (add Apply button after approval)

**Lifecycle:**
```
pending → approved → applied (applied_at set, baseline captured)
                   → measured (result_notes filled after next batch review)
        → rejected [terminal]
```

**Effort:** 3 hours

### 0.3 Fix Research Silent Drop (CRITICAL)

**What:** In `research_tasks.py`, when research status != "completed", still chain forward to brief generation (with degraded context). Don't mark task as succeeded with a failed status.

**Files:** `app/workers/research_tasks.py` (~line 169) — add chain-forward for non-completed research, mark pipeline step as "degraded" not "succeeded"

**Effort:** 30 min

### 0.4 BatchReview Recovery (HIGH)

**What:** Add cleanup for stuck BatchReviews. Two approaches (implement both):
1. Timeout: if "generating"/"reviewing" for >10 min, set to "failed"
2. API: `POST /batch-reviews/{id}/retry` re-runs generation

**Files:** `app/workers/janitor.py` (add batch review cleanup), `app/api/v1/batch_reviews.py` (add retry endpoint)

**Effort:** 2 hours

### 0.5 Pipeline Runs Page (HIGH)

**What:** Dashboard page listing pipeline runs with status, current step, lead name, duration. Filter by status (running/failed/succeeded). Click to see step context. Resume button for stuck runs.

**Files:** `dashboard/app/pipeline-runs/page.tsx` (new), `dashboard/lib/api/client.ts` (add `getPipelineRuns`, `resumePipeline`)

**Effort:** 1 day

### 0.6 Fix Brief Review Gate (HIGH)

**What:** In `brief_tasks.py:200-207`, only chain to `task_generate_draft` if `review_payload.approved` is True. If rejected, mark pipeline as "degraded" and skip draft.

**Files:** `app/workers/brief_tasks.py` (~line 200)

**Effort:** 30 min

### 0.7 Resume Endpoint Coverage (MEDIUM)

**What:** Add "research" step to the resume step_chain in `pipelines.py`. Map it to `task_generate_brief`.

**Files:** `app/api/v1/pipelines.py` (~line 121)

**Effort:** 15 min

**Definition of Done Phase 0:**
- [ ] Operator can see, approve, and reject proposals from dashboard
- [ ] Approved proposals transition to "applied" with baseline capture
- [ ] Research failures chain forward (degraded) instead of zombie
- [ ] Stuck BatchReviews cleaned up by janitor
- [ ] Pipeline runs visible with resume button
- [ ] Brief rejection gates draft generation
- [ ] Resume endpoint covers research branch
- [ ] All tests pass + tsc clean

---

## Phase 1 — Improve Reliability and Recovery (1 day)

### 1.1 Fix task_analyze_lead research chain failure handling

**What:** When `task_research_lead.delay()` fails for HIGH leads, fall back to `task_generate_draft.delay()` instead of abandoning the lead.

**Files:** `app/workers/pipeline_tasks.py` (~lines 287-298, 336-352)

### 1.2 Add error aggregation endpoint

**What:** `GET /api/v1/performance/errors` returning pipeline failures grouped by step, last 30 days.

**Files:** `app/api/v1/performance.py` (new endpoint), service query

### 1.3 Add try/except to batch review tasks

**What:** Wrap `task_check_batch_review` and `task_generate_batch_review_manual` bodies in try/except that sets BatchReview status="failed" on crash.

**Files:** `app/workers/batch_review_tasks.py`

### 1.4 Add crawl schedule to Celery Beat

**What:** Weekly territory crawl (configurable). Reuse batch_pipeline auto-crawl logic.

**Files:** `app/workers/celery_app.py` (beat_schedule), new task wrapper

**Definition of Done Phase 1:**
- [ ] HIGH leads that fail research still get drafts
- [ ] Error aggregation visible via API
- [ ] BatchReview tasks don't create zombies on crash
- [ ] Territory crawl runs on schedule

---

## Phase 2 — Make Batch Reviews Actionable (2-3 days)

### 2.1 Proposal application mechanism by category

**What:** When an approved proposal is applied:
- Category "scoring": update scoring weight override in OperationalSettings
- Category "channel": update default outreach channel recommendation
- Category "prompt": add hint to correction_hints (already implemented)
- Category "threshold": update batch review thresholds
- Category "workflow": advisory only (human implements)

**Files:** `app/services/pipeline/batch_review_service.py` (add `apply_proposal` with category routing)

### 2.2 Guardrail check after proposal application

**What:** After applying a proposal, capture key metrics. At next batch review, compare before/after. If metrics degraded, flag the proposal.

**Files:** `app/services/pipeline/batch_review_service.py` (add to `collect_batch_data`)

### 2.3 Temporal metric snapshots

**What:** Store weekly metric snapshots for trend analysis: correction rate, approval rate, reply rate, fallback rate. Display in Performance > IA tab as sparklines.

**Files:** New model `MetricSnapshot`, Celery Beat task, performance endpoint, dashboard component

**Definition of Done Phase 2:**
- [ ] Approved proposals can be applied by category
- [ ] Guardrail check detects degradation after application
- [ ] Weekly metric snapshots stored and visualized

---

## Phase 3 — Improve Operator Control and Clarity (1-2 days)

### 3.1 Attention queue / operator inbox

**What:** Single page showing items needing attention: pending proposals, failed pipelines, reviewer rejections, conversations needing takeover. Badge count on sidebar.

### 3.2 Runtime mode tooltips

**What:** Explain safe/assisted/outreach/closer in the RuntimeModePanel component.

### 3.3 Sidebar notification badges

**What:** Unread count badge on Notifications nav item. Count of pending proposals on AI Office.

### 3.4 Error aggregation dashboard

**What:** Component showing pipeline failures grouped by step, with frequency and last occurrence.

**Definition of Done Phase 3:**
- [ ] Operator knows what needs attention at a glance
- [ ] Runtime modes are explained
- [ ] Error patterns visible

---

## Phase 4 — Scale Automation Safely (1-2 days)

### 4.1 Low-risk proposal auto-apply

**What:** Proposals with category="scoring", confidence="high", impact="medium", AND 50+ outcomes can auto-apply with guardrail check. Feature-flagged.

### 4.2 WhatsApp inbound webhook

**What:** Endpoint receiving Kapso/Meta callbacks that auto-triggers `generate_closer_response`. Enables closer mode.

### 4.3 Draft auto-approval in assisted mode

**What:** When Reviewer approves draft with high confidence, auto-approve without operator.

### 4.4 Increase worker concurrency

**What:** Split into 2 workers (LLM queues + non-LLM queues), increase concurrency to 4.

**Definition of Done Phase 4:**
- [ ] Low-risk proposals auto-apply with guardrail
- [ ] Closer mode functions with inbound webhook
- [ ] Assisted mode approaches hands-off for high-confidence drafts
- [ ] Worker utilization matches hardware

---

## Phase 5 — Measure Real Commercial Improvement (ongoing)

### 5.1 Reply rate tracking by vertical/channel
### 5.2 Meeting rate correlation with proposal application
### 5.3 Win rate trending with confidence intervals
### 5.4 Proposal hit rate (% with positive impact)
### 5.5 Cost-per-lead-usable metric

**Definition of Done Phase 5:**
- [ ] Dashboard shows trending commercial metrics
- [ ] Proposal value is measurable
- [ ] Operator can decide safe→assisted transition with data

---

## Commit Strategy

Phase 0 commits (priority order):
1. `fix(pipeline): chain forward on research non-completed status`
2. `fix(pipeline): gate draft generation on brief review approval`
3. `fix(pipeline): add research step to resume endpoint`
4. `feat(pipeline): add proposal applied state and apply_proposal service`
5. `feat(api): add batch review proposal apply and retry endpoints`
6. `feat(pipeline): add batch review cleanup to janitor`
7. `feat(dashboard): add batch review proposals UI to AI Office`
8. `feat(dashboard): add pipeline runs page with resume`

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Proposal auto-apply cascades errors | Phase 4 only, with guardrail + 50-outcome gate |
| Research chain-forward sends degraded leads to draft | Mark as degraded in pipeline context; Executor sees "research degraded" |
| BatchReview cleanup kills in-progress reviews | 10-min timeout is generous; Executor+Reviewer rarely exceed 5 min |
| Pipeline runs page overwhelms with data | Paginate, default to last 50, filter by status |

---

## Expected Score Trajectory

| Phase | Operational Readiness | Key Change |
|-------|----------------------:|------------|
| Current | 5/10 | Three blockers |
| After Phase 0 | **7/10** | Blockers fixed, proposals usable, pipeline visible |
| After Phase 1 | **7.5/10** | Reliability + crawl schedule |
| After Phase 2 | **8/10** | Proposals actionable + temporal metrics |
| After Phase 3 | **8.5/10** | Operator clarity + attention routing |
| After Phase 4 | **9/10** | Automation scaled safely |
