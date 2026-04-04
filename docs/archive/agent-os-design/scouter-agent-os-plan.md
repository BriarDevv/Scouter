# Scouter Agent OS Plan

**Date:** 2026-04-03
**Source:** Agent Operating System Audit (`docs/audits/scouter-agent-operating-system-audit.md`)
**Approach:** Incremental, evidence-based, outcome-driven. Each phase validates before the next begins.

---

## Phase 0 — Clarify Hierarchy and Control

**Duration:** 1-2 weeks
**Type:** Documentation + minimal code

### Goal
Formalize the real agent hierarchy, eliminate ambiguity about who decides what, and establish the canonical agent docs structure.

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 0.1 | Create `docs/agents/hierarchy.md` with real power map from audit | Docs | S |
| 0.2 | Create `docs/agents/protocols.md` with communication and escalation rules | Docs | S |
| 0.3 | Create `docs/agents/governance.md` with approval gates and audit requirements | Docs | S |
| 0.4 | Create `docs/agents/mote/identity.md` consolidating SOUL.md + IDENTITY.md | Docs | S |
| 0.5 | Create `docs/agents/analyst/identity.md` for Executor role | Docs | S |
| 0.6 | Create `docs/agents/reviewer/identity.md` for Reviewer role | Docs | S |
| 0.7 | Create `docs/agents/coordinator/identity.md` for Leader role | Docs | S |
| 0.8 | Update `app/agent/prompts.py` to load from new `docs/agents/mote/identity.md` path (keep SOUL.md/IDENTITY.md as symlinks for backwards compat) | Backend | S |
| 0.9 | Update `docs/README.md` doc index to include new agents section | Docs | S |

### Definition of Done
- [ ] `docs/agents/` has hierarchy, protocols, governance, and per-agent identity files
- [ ] `SOUL.md` and `IDENTITY.md` are symlinks to `docs/agents/mote/identity.md`
- [ ] `prompts.py` loads from new path, tests pass
- [ ] No ambiguity about who controls what — documented in hierarchy.md

### Risks
- Over-documenting — keep identity files tight (< 50 lines each)
- Creating docs that don't match code — validate against audit findings

---

## Phase 1 — Restructure Agent MD Files and Skills

**Duration:** 2-3 weeks
**Type:** Documentation + backend prompt changes

### Goal
Give each agent role a proper identity that's injected into its prompts at runtime, and document all skills in a central registry.

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 1.1 | Create `docs/agents/skills-registry.md` inventorying all 55 tools + 7 skills | Docs | M |
| 1.2 | Create per-agent `decision-policy.md` files defining thresholds, criteria, tone | Docs | M |
| 1.3 | Create `docs/agents/reviewer/review-policy.md` with review criteria per type | Docs | S |
| 1.4 | Modify `app/llm/client.py` `invoke_structured()` to accept optional `identity_prompt` parameter | Backend | M |
| 1.5 | Create `app/llm/identity_loader.py` — loads identity .md file per role at invocation time | Backend | S |
| 1.6 | Inject Analyst identity into Executor prompts (lead analysis, draft gen, brief gen) | Backend | M |
| 1.7 | Inject Reviewer identity into Reviewer prompts (all review functions) | Backend | M |
| 1.8 | Add `skills/MODEL_ROUTING.md` enforcement as runtime validation (warn on misroute) | Backend | S |
| 1.9 | Update existing skills SKILL.md files to reference new identity structure | Docs | S |

### Definition of Done
- [ ] Every model invocation includes role identity context
- [ ] skills-registry.md is complete with all 55 tools categorized
- [ ] Review policy documented and injected into reviewer prompts
- [ ] Tests pass with identity injection

### Risks
- Identity prompts increasing token usage — keep under 200 tokens each
- Prompt regression — run existing test suite before/after

---

## Phase 2 — Internal Communication and Handoffs

**Duration:** 2-3 weeks
**Type:** Backend (models, migrations, worker changes)

### Goal
Enable structured handoff context between pipeline steps so each agent knows what happened before.

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 2.1 | Create `HandoffNote` SQLAlchemy model + Alembic migration | Backend | M |
| 2.2 | Create `handoff_service.py` with `emit_handoff()` and `get_handoffs_for_step()` | Backend | M |
| 2.3 | Modify `task_analyze_lead` to emit handoff note with quality decision + reasoning | Backend | S |
| 2.4 | Modify `task_research_lead` to emit handoff note with findings summary | Backend | S |
| 2.5 | Modify `task_generate_brief` to emit handoff note with opportunity assessment | Backend | S |
| 2.6 | Modify `task_review_brief` to emit handoff note with review verdict + corrections | Backend | S |
| 2.7 | Modify `task_generate_draft` to read preceding handoff notes and inject into prompt | Backend | M |
| 2.8 | Add handoff timeline to Activity page (`/activity`) | Frontend | M |
| 2.9 | Add handoff notes to Lead Detail pipeline section | Frontend | S |
| 2.10 | Create API endpoint `GET /api/v1/leads/{id}/handoffs` | Backend | S |

### Definition of Done
- [ ] Pipeline steps emit handoff notes with context
- [ ] Draft generation prompt includes brief review feedback and research highlights
- [ ] Activity page shows handoff timeline
- [ ] Lead detail shows per-step agent decisions

### Risks
- Handoff overhead — keep notes under 500 chars; structured JSON, not free text
- DB bloat — prune handoff notes for leads older than 90 days

---

## Phase 3 — Agent Memory and Learning

**Duration:** 3-4 weeks
**Type:** Backend (models, services, Celery tasks)

### Goal
Build the memory layer that allows agents to improve based on outcomes and reviewer feedback.

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 3.1 | Create `AgentMemory` model + migration (role, type, category, content, confidence, evidence_count) | Backend | M |
| 3.2 | Create `ReviewFeedback` model + migration (review_type, verdict, corrections, pattern_tags, severity) | Backend | M |
| 3.3 | Modify `review_service.py` to produce `ReviewFeedback` records from reviewer verdicts | Backend | M |
| 3.4 | Create `feedback_aggregation_service.py` — groups corrections by pattern, creates AgentMemory entries | Backend | L |
| 3.5 | Create `task_aggregate_feedback` Celery Beat task (daily) | Backend | M |
| 3.6 | Create `memory_injection_service.py` — retrieves top N relevant memories for a given role + context | Backend | M |
| 3.7 | Modify `invoke_structured()` to accept and inject memory block into system prompt | Backend | M |
| 3.8 | Inject Analyst memories into lead analysis + draft generation prompts | Backend | M |
| 3.9 | Create `SystemInsight` model + migration for cross-agent patterns | Backend | S |
| 3.10 | Create `outcome_correlation_service.py` — on WON/LOST, correlate to pipeline decisions | Backend | L |
| 3.11 | Wire outcome correlation to lead status change events | Backend | M |
| 3.12 | Add memory cap enforcement (100 per role, prune by confidence × recency) | Backend | S |

### Definition of Done
- [ ] Reviewer corrections produce structured feedback records
- [ ] Daily aggregation creates/reinforces agent memories
- [ ] Executor prompts include top 5 relevant learned patterns
- [ ] WON/LOST status changes trigger outcome correlation
- [ ] Memory table is capped and auto-pruned

### Risks
- Learning garbage — require minimum 3 evidence count before injecting into prompts
- Memory conflicts — surface conflicting patterns for human review, don't auto-resolve
- Prompt token budget — cap memory injection at 300 tokens

---

## Phase 4 — Agent Meetings and Synthesis

**Duration:** 1-2 weeks
**Type:** Backend (Celery tasks) + minimal frontend

### Goal
Automated periodic synthesis reports that consolidate agent learnings and surface actionable insights.

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 4.1 | Create `meeting_orchestration_service.py` | Backend | M |
| 4.2 | Create `task_daily_agent_sync` Celery Beat task — queries 24h data, produces daily report | Backend | M |
| 4.3 | Create `task_weekly_agent_retro` Celery Beat task — queries 7d data, produces weekly retro | Backend | M |
| 4.4 | Create `task_high_lead_council` — triggered per HIGH batch, reviews outcomes | Backend | M |
| 4.5 | Create `task_strategy_brief` Celery Beat task — weekly consolidated brief for Mote | Backend | M |
| 4.6 | Store meeting reports in DB (new `AgentReport` model) + optionally as .md files | Backend | M |
| 4.7 | Inject latest strategy brief into Mote's system prompt context | Backend | S |
| 4.8 | Add meeting report viewer to dashboard (simple list + detail page) | Frontend | M |

### Definition of Done
- [ ] Daily sync runs automatically and produces structured report
- [ ] Weekly retro synthesizes learnings and metric trends
- [ ] Strategy brief delivered to Mote's context
- [ ] Reports viewable in dashboard

### Risks
- Meeting reports becoming noise — include "actionable items" count; if zero, skip generation
- Coordinator (4b) quality — validate report quality; may need Executor (9b) for synthesis

---

## Phase 5 — AI Office Dashboard Layer

**Duration:** 3-4 weeks
**Type:** Frontend + API endpoints

### Goal
Dashboard pages that make the agent system visible, auditable, and operationally useful.

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 5.1 | Create `/agents` page — hierarchy visualization, per-agent status, health | Frontend | L |
| 5.2 | Create Agent Decision Log component — filterable timeline of all AI decisions | Frontend | L |
| 5.3 | Add model attribution to `TaskStatusRecord` API response | Backend | S |
| 5.4 | Add confidence scores to quality evaluation and classification responses | Backend | M |
| 5.5 | Create Agent Performance metrics API endpoint | Backend | M |
| 5.6 | Create `/agents/performance` page — accuracy, latency, approval rate per model | Frontend | L |
| 5.7 | Add memory viewer to `/agents` — current learnings per agent | Frontend | M |
| 5.8 | Add meeting report viewer to `/agents` or `/agents/reports` | Frontend | M |
| 5.9 | Enhance pipeline trace on Lead Detail — full DAG with model attribution | Frontend | M |
| 5.10 | Add handoff notes to pipeline trace visualization | Frontend | S |
| 5.11 | Create Agent Communication view — per-lead agent thread (handoffs + reviews) | Frontend | M |

### Definition of Done
- [ ] `/agents` page shows hierarchy, health, and per-agent metrics
- [ ] Decision log is filterable by agent, action, confidence, outcome
- [ ] Performance metrics show accuracy and latency trends
- [ ] Memory and reports are browsable from the dashboard
- [ ] Pipeline traces show which agent did what and why

### Risks
- Widget bloat — every component must answer "what decision does this help make?"
- Performance — paginate all lists, lazy-load charts, use server components

---

## Phase 6 — Outcome-Based Agent Improvement

**Duration:** 2-3 weeks
**Type:** Backend (services, prompt management)

### Goal
Close the loop: outcomes improve agent behavior automatically (with human oversight on canonical changes).

### Tasks

| # | Task | Type | Effort |
|---|---|---|---|
| 6.1 | Create prompt versioning system — track which prompt version produced which outcome | Backend | M |
| 6.2 | Create A/B framework for draft variations (tone, angle, CTA) | Backend | L |
| 6.3 | Vertical-specific memory injection — industry patterns into relevant prompts | Backend | M |
| 6.4 | Territory-specific memory injection — geographic patterns | Backend | S |
| 6.5 | Automatic prompt improvement proposals — when memory confidence ≥ 0.8, propose prompt delta | Backend | M |
| 6.6 | Prompt proposal review UI — Mote or human reviews and approves/rejects proposals | Frontend | M |
| 6.7 | Create "System Intelligence Score" composite metric | Backend | M |
| 6.8 | Add evolution tracking to Agent Performance page — show improvement trends | Frontend | S |

### Definition of Done
- [ ] Prompt versions are tracked and correlatable to outcomes
- [ ] A/B variations running for at least one draft dimension
- [ ] Industry/territory patterns injected into relevant prompts
- [ ] Prompt improvement proposals generated automatically
- [ ] System Intelligence Score measurable and trending

### Risks
- Premature optimization — require minimum 50 leads through a prompt version before comparing
- A/B complexity — start with 2 variations max, expand only with clear signal
- Canonical changes — all prompt modifications require explicit approval

---

## Commit Strategy

Each phase should be a **feature branch** with atomic commits:

```
Phase 0: feat(agents): formalize agent hierarchy and identity docs
Phase 1: feat(agents): add per-role identity injection and skills registry
Phase 2: feat(pipeline): add handoff notes between pipeline steps
Phase 3: feat(memory): add agent memory and reviewer feedback loop
Phase 4: feat(meetings): add automated agent synthesis reports
Phase 5: feat(dashboard): add AI Office dashboard pages
Phase 6: feat(learning): add outcome-based agent improvement
```

### PR Breakdown

| Phase | PRs | Reviewability |
|---|---|---|
| 0 | 1 (docs-only) | Easy — all markdown |
| 1 | 2 (docs + backend) | Medium — prompt changes need testing |
| 2 | 3 (model + workers + frontend) | Medium — migration + task changes |
| 3 | 3-4 (models + services + injection + correlation) | Hard — core learning system |
| 4 | 2 (backend tasks + frontend viewer) | Medium |
| 5 | 3-4 (API + pages, split by feature) | Medium-Hard — multiple new pages |
| 6 | 3 (versioning + A/B + proposals) | Hard — outcome tracking |

---

## Risks

| Risk | Mitigation |
|---|---|
| Memory becomes noise | Confidence threshold (≥ 0.6), evidence minimum (≥ 3), auto-prune |
| Feedback loops amplify bias | Always correlate to outcomes, not approvals |
| Dashboard widget bloat | Each widget must answer "what decision does this help?" |
| Prompt token budget overflow | Cap identity (200 tok), memory (300 tok), handoff (200 tok) |
| Model VRAM conflicts | Keep executor warm, load reviewer on demand, coordinator brief |
| Canonical file drift | All changes via PR or Mote-proposal → human approval |
| Overengineering | Validate each phase improves a measurable metric before starting next |
| Scope creep | Phases are independent; stop at any phase boundary if value plateaus |

---

## Definition of Done by Phase

| Phase | Key Metric | Pass Criteria |
|---|---|---|
| 0 | Documentation completeness | All roles documented, hierarchy unambiguous |
| 1 | Prompt quality | Reviewer approval rate improves or holds after identity injection |
| 2 | Pipeline transparency | Every HIGH lead has full handoff trail visible in dashboard |
| 3 | Learning evidence | ≥ 10 AgentMemory entries with evidence_count ≥ 3 within 2 weeks |
| 4 | Report value | ≥ 1 actionable item per weekly retro |
| 5 | Operator utility | Operator can answer "why did the system do X?" from dashboard |
| 6 | System improvement | Measurable improvement in reply_rate or conversion_rate over 30 days |

---

## Timeline Summary

```
Phase 0 ████░░░░░░░░░░░░░░░░░░░░ (weeks 1-2)
Phase 1 ░░░░████████░░░░░░░░░░░░ (weeks 3-5)
Phase 2 ░░░░░░░░░░░░████████░░░░ (weeks 6-8)
Phase 3 ░░░░░░░░░░░░░░░░████████████ (weeks 9-12)
Phase 4 ░░░░░░░░░░░░░░░░░░░░████░░░░ (weeks 11-12, parallel with late Phase 3)
Phase 5 ░░░░░░░░░░░░░░░░░░░░░░░░████████████ (weeks 13-16)
Phase 6 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████████ (weeks 17-19)
```

**Total estimated: 16-19 weeks** for full Agent OS layer.
**Phase 0 alone** delivers immediate clarity at near-zero risk.
