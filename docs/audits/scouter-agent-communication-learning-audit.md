# Scouter Agent Communication, Learning & Comfort Audit

**Date:** 2026-04-05
**Auditor:** Claude Opus 4.6 — 4 parallel specialist agents
**Scope:** Inter-agent communication, learning/memory, dashboard visibility, actor comfort

---

## Executive Summary

Scouter's 4 AI actors **never communicate directly with each other**. All "communication" is indirect, unidirectional data flowing through PostgreSQL via `step_context_json`. The system has **zero closed feedback loops** — corrections, outcomes, and weekly reports are stored and displayed but never change agent behavior. The dashboard shows 40% of available AI data, leaving operators blind to conversations, learning, and outcome insights. Each actor operates in isolation: Mote can't explain what happened to a lead, Scout forgets everything between investigations, Executor never sees Reviewer's corrections, and Reviewer's revisions are never applied to drafts.

---

## 1. Agent Communication Map

```
                     DIRECT COMMUNICATION: NONE

     INDIRECT (step_context_json, pipeline-forward only):

     Enrichment → Scoring → Analysis → Scout → Research → Brief → Review
                                 |                                    |
                                 v                                    v
                           Scout reads                        All accumulated
                           "analysis"                         context read by
                           context                            Executor (draft)
                                                                     |
                                                                     v
                                                              Reviewer reviews
                                                                     |
                                                                     v
                                                              review_corrections
                                                                     |
                                                                DEAD END

     PERIODIC DIGEST (weekly, broadcast-only):

     All DB tables --[counts]--> weekly_tasks --[500 chars]--> Mote system prompt

     MISSING PATHS:
     - Reviewer corrections --> Executor prompts (learning loop)
     - Reviewer revised_body --> actual draft update (auto-apply)
     - Scout findings --> Mote tools (agent awareness)
     - Outcome data --> scoring weights (auto-tuning)
     - Mote --> Scout (on-demand investigation trigger)
     - Any bidirectional communication between any pair
     - Any cross-session memory for any actor
```

### Key Facts
- Mote and Scout share zero state. Mote cannot see Scout's investigation threads.
- Executor and Reviewer are one-way: Executor generates → Reviewer reviews → corrections stored → nobody reads them back.
- The only "meeting" is the weekly synthesis — a broadcast digest, not a discussion.
- `step_context_json` is write-once, read-at-end — not a conversation between steps.

---

## 2. Learning & Memory Audit

### Feedback Loops — ALL OPEN

| Loop | Data collected | Where it ends | Closes? |
|------|---------------|---------------|---------|
| Reviewer → Executor | Corrections with category/severity/issue/suggestion | `review_corrections` table | **NO** — never injected into prompts |
| Outcomes → Scoring | Signal correlations, win rates, weight recommendations | Advisory text in weekly report | **NO** — scoring weights hardcoded in `rules.py` |
| Weekly → Mote | Synthesis of all metrics + recommendations | 500 chars in Mote's system prompt | **COSMETIC** — too truncated to be actionable |
| Scout memory | Tool calls, pages, findings per investigation | `investigation_threads` table | **NO** — Scout has total amnesia between leads |
| Mote memory | Conversation history (50 msgs per conversation) | Per-conversation only | **NO** — zero cross-session memory |
| Prompt evolution | prompt_version labels on invocations | Tracking labels only | **NO** — all prompts are static string constants |

### What Each Actor Remembers vs Forgets

| Actor | Remembers (within session) | Forgets (between sessions) |
|-------|--------------------------|---------------------------|
| Mote | Last 50 messages in current conversation | Everything from past conversations, operator preferences |
| Scout | Current investigation tool calls/results | All past investigations, industry patterns |
| Executor | Current prompt context (pipeline accumulated) | All past generations, correction patterns |
| Reviewer | Current artifact being reviewed | All past reviews, own correction history |

---

## 3. Dashboard Visibility

### Coverage: 5/10

| Shown | Not Shown (backend exists) |
|-------|--------------------------|
| Agent status cards (4 agents) | Mote outbound conversations (12 orphaned endpoints) |
| Decision log (function/role/latency) | Weekly reports |
| Scout investigations summary | Outcome learning / signal correlations |
| AI health (approval rate, fallback rate) | Scoring recommendations |
| Top correction categories | Conversation takeover UI |
| Lead AI panel (analysis, brief, review) | Draft generation step in AI journey |
| | Pipeline step-by-step progress |
| | Agent communication flow visualization |

### 12 Orphaned Backend Endpoints
All in `app/api/v1/ai_office.py` and `app/api/v1/performance.py` — fully functional, zero frontend consumers.

---

## 4. Actor Comfort Scores

| Actor | Context | Scope | Integration | Overall | Top Friction |
|-------|--------:|------:|------------:|--------:|-------------|
| Mote | 5 | 6 | 4 | **5/10** | Can't explain lead journey — no pipeline data in tools |
| Scout | 7 | 8 | 6 | **7/10** | `search_competitors` scrapes Google HTML (fragile) |
| Executor | 8 | 8 | 7 | **8/10** | Never sees Reviewer's corrections from prior runs |
| Reviewer | 7 | 7 | 5 | **6/10** | `revised_body` captured but never applied to drafts |

---

## 5. Top 15 Findings

| # | Sev | Category | Finding |
|---|-----|----------|---------|
| 1 | HIGH | learning | Zero closed feedback loops — all 6 loops are open |
| 2 | HIGH | communication | Zero direct agent-to-agent communication paths |
| 3 | HIGH | learning | Reviewer corrections never reach Executor prompts |
| 4 | HIGH | learning | Reviewer's `revised_body` captured but never applied to drafts |
| 5 | HIGH | dashboard | 12 backend AI endpoints have zero frontend consumers |
| 6 | HIGH | comfort | Mote can't explain lead journey — `get_lead_detail` has no pipeline data |
| 7 | MEDIUM | learning | Scoring weights hardcoded — outcome recommendations are advisory only |
| 8 | MEDIUM | communication | Weekly synthesis truncated to 500 chars — recommendations cut off |
| 9 | MEDIUM | comfort | Mote's 55 tools listed flat with no category grouping |
| 10 | MEDIUM | dashboard | Performance page is pure funnel metrics — zero AI content |
| 11 | MEDIUM | learning | Scout has total amnesia between investigations |
| 12 | MEDIUM | learning | Mote has zero cross-session memory |
| 13 | MEDIUM | comfort | Scout's `search_competitors` scrapes Google HTML (unreliable) |
| 14 | LOW | dashboard | Lead AI journey panel missing draft generation step |
| 15 | LOW | learning | Prompts are static string constants — no runtime adaptation |

---

## 6. Top 10 Improvements (by impact/effort)

| # | Improvement | Effort | Impact |
|---|-------------|--------|--------|
| 1 | Add `get_lead_journey` tool for Mote (step_context + corrections + delivery) | Low | HIGH |
| 2 | Auto-apply Reviewer's `revised_body` to drafts when verdict="revise" | Low | HIGH |
| 3 | Inject top-3 correction patterns into Executor draft prompts | Medium | HIGH |
| 4 | Wire Mote conversations into AI Office dashboard | Medium | HIGH |
| 5 | Add Outcome Learning tab to Performance page (4 existing endpoints) | Medium | HIGH |
| 6 | Expand weekly context from 500→1500 chars, use structured format | Low | MEDIUM |
| 7 | Add `trigger_scout_investigation` tool for Mote | Low | MEDIUM |
| 8 | Group Mote's 55 tools by category in schema | Low | MEDIUM |
| 9 | Add scoring_overrides table for outcome-based weight adjustment | Medium | HIGH |
| 10 | Show weekly reports in AI Office page | Low | MEDIUM |
