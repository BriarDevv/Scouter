# Scouter Agent Hierarchy

**Last updated:** 2026-04-03
**Source:** Agent OS Audit

---

## Current Hierarchy (as of audit)

```
Human Operator (ultimate authority)
│
├── Mote (hermes3:8b) — Agent
│   Role: Conversational AI, user interface, tool orchestration
│   Authority: Full read access, confirmation-gated writes
│   Identity: SOUL.md + IDENTITY.md (runtime-loaded)
│   Tools: 55 (22 require confirmation, 33 not gated)
│   Channels: Web (SSE), WhatsApp (webhook), Telegram (webhook)
│   Memory: Conversation only (last 50 messages)
│
├── Executor (qwen3.5:9b) — "Analyst" in proposed hierarchy
│   Role: Primary generation and analysis workhorse
│   Authority: Generates on demand, no autonomous decisions
│   Identity: None (stateless invocation)
│   Tasks: Lead quality, summaries, drafts, briefs, dossiers, classification
│   Queue: llm
│   Memory: None
│
├── Reviewer (qwen3.5:27b) — Quality Gate
│   Role: Second opinion on leads, drafts, briefs, inbound messages
│   Authority: Evaluates on demand, toggled by ops.reviewer_enabled
│   Identity: None (stateless invocation)
│   Tasks: Lead review, draft review, brief review, reply review
│   Queue: reviewer
│   Memory: None
│
└── Leader (qwen3.5:4b) — "Coordinator" in proposed hierarchy
    Role: Lightweight summarization
    Authority: Summarizes grounded data only
    Identity: None (stateless invocation)
    Tasks: Brief summaries (scouter-briefs skill only)
    Queue: N/A (inline)
    Memory: None
```

---

## Power Map: Who Decides What

| Decision Domain | Decision Maker | Override Authority |
|---|---|---|
| Lead quality (HIGH/MEDIUM/LOW) | Analyst (9b) via `evaluate_lead_quality_structured()` | Code routing in `pipeline_tasks.py` |
| Pipeline routing (HIGH vs LOW lane) | Hardcoded in `pipeline_tasks.py:336-360` | No runtime override |
| Contact method recommendation | Analyst (9b) via `generate_commercial_brief_structured()` | Human can change in UI |
| Draft content | Analyst (9b) via outreach generator | Human edits before send |
| Draft quality verdict | Reviewer (27b) via `review_draft_with_reviewer()` | Human overrides |
| Send approval | Human operator | Final authority |
| Feature toggles | Human operator via Settings | Immediate effect |
| Mote tool execution | Human confirmation for 22 tools | Can deny any tool |
| Pipeline start/stop | Human operator via Dashboard | Immediate effect |

---

## Proposed Future Hierarchy

```
Human Operator (ultimate authority)
│
├── Mote (hermes3:8b) — Chief Intelligence Officer
│   New: Receives strategy briefs, reviews proposals, evolves system
│   New: Memory of operator preferences and system performance
│
├── Analyst (qwen3.5:9b) — Analysis & Generation Agent
│   New: Has identity and decision policies
│   New: Receives learned patterns from memory layer
│   New: Emits handoff notes for downstream steps
│
├── Reviewer (qwen3.5:27b) — Quality Assurance Agent
│   New: Has review policies and feedback format
│   New: Corrections aggregated into Analyst memory
│   New: Performance tracked (approval rate, common issues)
│
└── Coordinator (qwen3.5:4b) — Operational Synthesis Agent
    New: Daily syncs, weekly retros, strategy briefs
    New: Report generation from aggregated data
    New: Alert triage and escalation
```

---

## Authority Boundaries

### Autonomous (no approval needed)
- Read any data
- Generate analysis, summaries, quality ratings
- Produce handoff notes
- Create memory entries (capped, with confidence)
- Generate meeting reports

### Requires Human Confirmation
- Create/update/delete leads
- Generate/approve/reject/send outreach
- Modify operational settings
- Start/stop pipelines or crawls
- Promote learnings to canonical rules

### Never Autonomous
- Send outreach without approval (in safe/assisted mode)
- Modify agent identity or hierarchy files
- Delete data
- Change security settings
- Override human decisions
