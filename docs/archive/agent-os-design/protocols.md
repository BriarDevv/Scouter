# Scouter Agent Protocols

**Last updated:** 2026-04-03
**Source:** Agent OS Audit

---

## 1. Pipeline Communication Protocol

### Current State
Pipeline steps communicate via Celery `.delay()` with `(lead_id, pipeline_run_id, correlation_id)`. Each step re-fetches the lead from DB. No context about previous step's reasoning is passed.

### Target Protocol: Handoff Notes

Every pipeline step that involves an LLM decision should emit a `HandoffNote` before dispatching the next step:

```
From Step → HandoffNote → To Step
  - from_step: "analyze_lead"
  - to_step: "research_lead"
  - from_role: EXECUTOR
  - context: { "quality": "high", "reasoning": "...", "key_signals": [...] }
  - confidence: 0.85
```

The receiving step reads handoff notes and injects relevant context into its prompt.

### Handoff Points

| From | To | What to Communicate |
|---|---|---|
| `task_analyze_lead` | `task_research_lead` | Quality decision, key signals, suggested research focus |
| `task_analyze_lead` | `task_generate_draft` (LOW) | Quality summary, suggested angle |
| `task_research_lead` | `task_generate_brief` | Research findings, digital maturity, WhatsApp presence |
| `task_generate_brief` | `task_review_brief` | Opportunity assessment, confidence areas, weak points |
| `task_review_brief` | `task_generate_draft` | Review verdict, corrections, what to emphasize in draft |

---

## 2. Reviewer Feedback Protocol

### Current State
Reviewer produces verdict + reasoning as free text. Stored in DB but never aggregated or fed back.

### Target Protocol: Structured Feedback

Every review produces a `ReviewFeedback` record:

```
ReviewFeedback:
  review_type: "draft_review"
  target_id: draft_id
  verdict: "needs_improvement"
  corrections: [
    { "category": "tone", "issue": "too formal for WhatsApp", "suggestion": "use casual AR Spanish" },
    { "category": "personalization", "issue": "generic opener", "suggestion": "reference specific signal" }
  ]
  pattern_tags: ["tone_mismatch", "weak_personalization"]
  severity: "moderate"
```

### Feedback Aggregation Rules

1. **Daily**: Group corrections by `pattern_tags` across all reviews
2. **Threshold**: If a pattern appears ≥ 3 times in 7 days → create `AgentMemory` entry
3. **Injection**: Top 5 memories by confidence injected into Analyst's next relevant prompt
4. **Decay**: Memories not reinforced in 30 days lose 20% confidence; pruned below 0.3

---

## 3. Model Routing Protocol

### Authoritative Rules (from `skills/MODEL_ROUTING.md`)

| Role | Model | Use For | Never Use For |
|---|---|---|---|
| Leader (4b) | qwen3.5:4b | Summaries, briefs, prioritization (after grounded data) | Independent decisions, classification |
| Executor (9b) | qwen3.5:9b | Classification, drafts, quality evaluation, pipeline tasks | Simple data lookups |
| Reviewer (27b) | qwen3.5:27b | On-demand second opinions, quality reviews | Routine classification, auto-invocation |
| Agent (8b) | hermes3:8b | Interactive chat, tool orchestration | Batch pipeline tasks |

### Routing Enforcement
- Model resolution: `app/llm/resolver.py` → `resolve_model_for_role(role)`
- Default timeout by role: Leader/Executor 120s, Agent 180s, Reviewer 360s (configurable via env vars)
- Retry: 3 attempts with exponential backoff (2s, 4s, 8s)
- Fallback: Per-domain factory functions return safe defaults

---

## 4. Escalation Protocol

### When to Escalate to Human

| Condition | Action |
|---|---|
| LLM returns FALLBACK status | Log warning, continue with safe default |
| LLM returns FAILED status | Stop pipeline step, mark task failed, notify operator |
| Reviewer verdict is "reject" | Flag draft for human review |
| Inbound classified as `needs_human_review` | Notification to operator |
| Lead score ≥ notification threshold | Alert via WhatsApp/Telegram (if enabled) |
| Pipeline task exceeds soft time limit (5min) | SoftTimeLimitExceeded → mark retrying |
| Pipeline task exceeds hard time limit (6min) | Hard kill → mark failed |
| Same task fails 3 times | Stop retrying, mark failed, notify operator |

### When to Escalate to Mote

| Condition | Action |
|---|---|
| Strategy brief generated | Inject into Mote's context |
| Agent memory conflict detected | Surface in next strategy brief |
| Metric anomaly (>2 std dev) | Include in daily sync report |
| New pattern with high confidence | Include in weekly retro |

---

## 5. Confirmation Gate Protocol

### Mote Tool Confirmation

22 tools require human confirmation before execution:

1. Agent calls tool marked `requires_confirmation=True`
2. Tool execution is paused, status set to "pending"
3. `ConfirmationRequired` event yielded to transport layer
4. User sees confirmation prompt with tool name and arguments
5. User approves → tool executes → result returned to agent loop
6. User denies → tool skipped → agent receives denial notice

### Max Tool Loops
- 5 tool-call loops per agent turn (prevents runaway execution)
- After 5 loops: agent forced to produce final text response

---

## 6. Memory Access Protocol

### Who Can Write What

| Agent | Can Write | Cannot Write |
|---|---|---|
| Analyst | Own operational memory (patterns, errors) | Canonical files, other agent memory |
| Reviewer | Feedback records, own memory | Canonical files, Analyst memory directly |
| Coordinator | Meeting reports, synthesized insights | Canonical files, agent memories |
| Mote | Strategy proposals, operator preferences | Canonical files (proposes, doesn't commit) |

### Memory Injection Rules

1. Only inject memories with `confidence ≥ 0.6` AND `evidence_count ≥ 3`
2. Maximum 5 memories per invocation (sorted by relevance × confidence)
3. Total memory token budget: 300 tokens
4. Memory must match context (same industry, same review_type, etc.)
5. Conflicting memories: include both with confidence scores, let model decide

### Memory Lifecycle

```
Observation → Memory(confidence=0.3, evidence=1)
  → Reinforced → Memory(confidence=0.5, evidence=3)
  → Reinforced → Memory(confidence=0.7, evidence=8) → Eligible for prompt injection
  → 30 days without reinforcement → confidence × 0.8
  → confidence < 0.3 → Pruned
```

---

## 7. Meeting Protocol

### Daily Agent Sync (automated)

**Trigger:** Celery Beat, daily or every N pipelines
**Producer:** Coordinator (4b)
**Input:** Last 24h of task runs, review feedback, notifications, lead status changes
**Output format:**

```markdown
# Daily Agent Sync — YYYY-MM-DD

## Key Numbers
- Leads processed: N
- HIGH leads: N
- Drafts generated: N
- Reviews: N approved / N rejected
- Inbound classified: N

## Notable Events
- [list of significant items]

## Patterns Detected
- [any recurring issues or successes]

## Actionable Items
- [specific follow-ups needed]
```

**Delivery:** Stored in DB, available in dashboard, injected into Mote context

### Weekly Retro (automated)

**Trigger:** Celery Beat, weekly
**Producer:** Coordinator (4b) or Executor (9b) for depth
**Input:** 7-day aggregation of daily syncs + outcome data
**Output:** Trends, improvements, degradations, memory promotions, rule proposals

### HIGH Lead Council (event-triggered)

**Trigger:** After batch of HIGH leads complete pipeline
**Producer:** Coordinator synthesizing Analyst + Reviewer data
**Input:** HIGH lead outcomes, brief accuracy, contact method effectiveness
**Output:** What worked, what didn't, proposed improvements to HIGH lane

---

## 8. Report Delivery Protocol

### How Reports Reach Mote

1. Reports stored in `AgentReport` DB table
2. Latest strategy brief ID stored in operational settings
3. `build_agent_system_prompt()` modified to include latest brief summary
4. Mote can query reports via `list_agent_reports` tool (future)

### How Reports Reach Human

1. Reports viewable in dashboard (`/agents/reports` page, future)
2. Critical reports trigger notification (WhatsApp/Telegram if enabled)
3. Weekly retro summary included in Mote's welcome context

---

## 9. Governance Rules

### Canonical File Changes

Files in `docs/agents/*/identity.md`, `hierarchy.md`, `protocols.md`, and `governance.md` are **canonical** and require:

1. Change proposed by Mote or Coordinator via report
2. Human reviews proposal
3. Human applies change via commit
4. No automated writes to canonical files

### Runtime Memory Changes

`AgentMemory` and `SystemInsight` records are **runtime** and can be:

1. Created automatically by aggregation services
2. Reinforced by repeated observations
3. Pruned automatically when confidence decays
4. Never promoted to canonical files without human approval

### Generated Reports

Meeting reports, syncs, and retros are **generated** artifacts:

1. Created automatically by scheduled tasks
2. Stored in DB with timestamp and producer
3. Optionally exported as .md to `docs/reports/`
4. Read-only for all agents except the producer
