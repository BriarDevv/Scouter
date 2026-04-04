# Scouter Agent Operating System Audit

**Date:** 2026-04-03
**Scope:** Full audit of the multi-agent system — hierarchy, communication, memory, skills, dashboard, and commercial integration.
**Method:** Automated deep-read of all LLM, agent, worker, workflow, service, skill, .md, and dashboard files in the codebase.

---

## 1. Executive Summary

Scouter operates a **four-role LLM system** (Leader, Executor, Reviewer, Agent) powered by local Ollama models. However, only **one true agent exists** — Mote (Hermes 3 8B) — which orchestrates through 55 tools. The other three roles (Leader/Executor/Reviewer) are **stateless model invocations**, not agents with identity, memory, or decision continuity.

The system has strong foundations: role-based model routing, structured invocations with fallback, a well-governed tool registry with confirmation gates, full task tracking with correlation IDs, and a quality-based pipeline bifurcation (HIGH/LOW lanes). These are real, production-grade capabilities.

**What's missing** is the *nervous system* between these capabilities: no inter-agent communication beyond DB writes, zero learning or feedback mechanisms, no memory that persists across pipelines, and limited dashboard visibility into AI decisions. The current architecture is a **pipeline with smart models**, not yet an **agent operating system**.

### Key Findings

| Dimension | Current State | Gap |
|---|---|---|
| **Hierarchy** | 4 model roles, 1 real agent (Mote) | Roles are model aliases, not agents with identity |
| **Communication** | DB writes + Celery .delay() chains | No handoff messages, no inter-agent feedback |
| **Memory** | Zero — no learning, no pattern storage | No memory layer at any level |
| **Governance** | Strong for Mote (22 confirmation-gated tools) | No governance framework for autonomous model decisions |
| **Skills** | 7 well-structured SKILL.md files for Mote | No skills for Executor/Reviewer/Leader roles |
| **Dashboard** | Partial attribution (Activity page, Responses) | No AI Office view, no decision transparency |
| **Feedback loops** | None | No outcome-to-improvement cycle |

---

## 2. Current Agent Reality

### What Actually Exists

The system has **four model roles** and **one agent**:

| Entity | Model | Is an Agent? | Has Identity? | Has Memory? | Has Tools? | Makes Decisions? |
|---|---|---|---|---|---|---|
| **Mote** | hermes3:8b | **Yes** | Yes (SOUL.md + IDENTITY.md) | Conversation only (50 msgs) | 55 tools | Yes, with confirmation gates |
| **Leader** | qwen3.5:4b | No — stateless invocation | No | No | No | Summarizes; doesn't decide |
| **Executor** | qwen3.5:9b | No — stateless invocation | No | No | No | Generates on demand |
| **Reviewer** | qwen3.5:27b | No — stateless invocation | No | No | No | Evaluates on demand |

### What Each Role Actually Does at Runtime

**Mote (Agent — hermes3:8b)**
- Conversational AI with streaming tool-calling loop
- Builds system prompt dynamically from SOUL.md + IDENTITY.md + live stats + tool schemas
- Loads last 50 messages as context
- Max 5 tool-call loops per turn
- 3 channels: Web (SSE), WhatsApp (webhook), Telegram (webhook)
- Cross-channel conversation sync
- File: `app/agent/core.py:200-349`

**Leader (qwen3.5:4b)**
- Used only for `scouter-briefs` skill (Mote's tool layer)
- Summarizes grounded data — never used for independent decisions
- No direct pipeline involvement
- Referenced in `skills/MODEL_ROUTING.md` but has no code-level orchestration role

**Executor (qwen3.5:9b)**
- Primary workhorse — handles 13 prompt definitions:
  - Business summary, lead quality evaluation, outreach drafts (email + WhatsApp), inbound reply classification, reply assistant drafts, dossier generation, commercial brief generation
- Invoked by workers on `llm` queue
- No identity, no context beyond the current prompt
- File: `app/llm/invocations/` (5 domain files)

**Reviewer (qwen3.5:27b)**
- Quality gate — handles 5 review prompts:
  - Lead review, outreach draft review, inbound reply review, reply assistant draft review, commercial brief review
- Invoked by workers on `reviewer` queue
- Toggled by `ops.reviewer_enabled` setting
- Terminal tasks — never chains to next step
- File: `app/services/review_service.py:19-157`

---

## 3. Real Hierarchy vs Assumed Hierarchy

### Assumed Hierarchy (from docs and naming)

```
Hermes/Mote (Leader)
  ├── Executor (does the work)
  ├── Reviewer (checks the work)
  └── Leader model (orchestrates)
```

### Real Hierarchy (from code)

```
Human Operator
  └── Mote (hermes3:8b) — conversational interface, tool executor
        ├── calls Executor (qwen3.5:9b) — via tools that trigger LLM invocations
        └── calls Reviewer (qwen3.5:27b) — via review tools

Celery Pipeline (independent of Mote)
  └── task_full_pipeline → task_enrich_lead → task_score_lead → task_analyze_lead
        ├── HIGH lane → task_research_lead → task_generate_brief → task_review_brief → task_generate_draft
        └── LOW lane → task_generate_draft
```

### Key Contradictions

1. **"Hermes is the leader"** — Partially true. Mote is the user-facing agent but does NOT orchestrate the Celery pipeline. The pipeline runs independently via hardcoded task chains.

2. **"Qwen 4B is the orchestrator"** — False. Leader (4b) is barely used — only for summaries in the briefs skill. It has no routing or decision authority.

3. **"Who has the last word?"** — The **code** does. Pipeline routing (HIGH vs LOW) is decided by the Executor model's quality evaluation, then hardcoded in `pipeline_tasks.py:336-360`. There is no "leader" making runtime routing decisions.

4. **"Who decides the HIGH lane?"** — `evaluate_lead_quality_structured()` (Executor, qwen3.5:9b) returns `quality ∈ {high, medium, low}`. This single LLM call determines the entire downstream path.

5. **"Who decides contact channel?"** — `generate_commercial_brief_structured()` (Executor) returns `recommended_contact_method`. This is respected by `outreach_draft_generation.py:83-92`.

### The Real Power Map

| Decision | Who Decides | Where |
|---|---|---|
| Lead quality (HIGH/MEDIUM/LOW) | Executor (9b) | `lead_pipeline.py:62` |
| Contact method (email/whatsapp/call) | Executor (9b) via brief | `outreach_draft_generation.py:83` |
| Draft content | Executor (9b) | `outreach/generator.py` |
| Draft quality approval | Reviewer (27b) | `review_service.py:60` |
| Pipeline routing | Hardcoded in task chains | `pipeline_tasks.py:336` |
| Send approval | Human operator | Dashboard UI |
| Feature toggles | Human operator | Settings page |
| Mote tool execution | Human confirmation | `agent/core.py:282` |

---

## 4. Model Map and Responsibilities

### Model Configuration

| Role | Env Variable | Default | Timeout | Queue |
|---|---|---|---|---|
| Leader | `OLLAMA_LEADER_MODEL` | qwen3.5:4b | 120s | N/A (inline) |
| Executor | `OLLAMA_EXECUTOR_MODEL` | qwen3.5:9b | 120s | `llm` |
| Reviewer | `OLLAMA_REVIEWER_MODEL` | qwen3.5:27b | 360s | `reviewer` |
| Agent | `OLLAMA_AGENT_MODEL` | hermes3:8b | 180s | N/A (streaming) |

Source: `app/core/config.py:28-41`, `app/llm/catalog.py:4-16`

### Invocation Map (13 prompt definitions)

| Prompt ID | Role | Domain | Output |
|---|---|---|---|
| `BUSINESS_SUMMARY_PROMPT` | Executor | Lead | Business description |
| `LEAD_QUALITY_PROMPT` | Executor | Lead | quality (high/medium/low) + reasoning |
| `LEAD_REVIEW_PROMPT` | Reviewer | Lead | verdict + reasoning |
| `OUTREACH_DRAFT_PROMPT` | Executor | Outreach | subject + body |
| `OUTREACH_DRAFT_REVIEW_PROMPT` | Reviewer | Outreach | verdict + tone + personalization + CTA |
| `WHATSAPP_DRAFT_PROMPT` | Executor | Outreach | WhatsApp message |
| `INBOUND_REPLY_CLASSIFICATION_PROMPT` | Executor | Reply | label (10 categories) + summary |
| `INBOUND_REPLY_REVIEW_PROMPT` | Reviewer | Reply | verdict + escalation |
| `REPLY_ASSISTANT_DRAFT_PROMPT` | Executor | Reply | response draft |
| `REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT` | Reviewer | Reply | verdict |
| `DOSSIER_PROMPT` | Executor | Research | structured dossier |
| `COMMERCIAL_BRIEF_PROMPT` | Executor | Research | opportunity analysis |
| `COMMERCIAL_BRIEF_REVIEW_PROMPT` | Reviewer | Research | verdict |

Source: `app/llm/prompt_registry.py`, `app/llm/prompts.py` (606 lines)

### Resilience Architecture

Three-layer fallback: Network retry (3 attempts, exponential backoff) → JSON parse recovery (`_extract_json()`) → Fallback factory (safe defaults).

Every invocation logged to `LLMInvocation` table with: status, model, latency_ms, fallback_used, degraded, parse_valid, correlation_id, lead_id.

Source: `app/llm/client.py:313-589`

---

## 5. Current MD / Prompt / Skill Structure

### Runtime-Loaded Files (consumed by code)

| File | Consumer | Purpose |
|---|---|---|
| `SOUL.md` | `app/agent/prompts.py:42-53` | Mote persona — identity, limits, pipeline model, tone |
| `IDENTITY.md` | `app/agent/prompts.py:42-53` | Mote metadata — name, role, model stack |
| `HEARTBEAT.md` | `app/agent/prompts.py` (reserved) | Empty — reserved for periodic tasks |

### Documentation-Only Files (NOT loaded at runtime)

| File | Purpose |
|---|---|
| `AGENTS.md` | AI assistant entrypoint |
| `skills/MODEL_ROUTING.md` | Routing rules reference (not enforced in code) |
| `skills/*/SKILL.md` (8 files) | Skill definitions for Mote |
| `docs/agents/context.md` | Secondary operator/agent context |
| `.claude/commands/*.md` (7 files) | Developer workflow commands |

### Skill Inventory

| Skill | Mutating? | Model Used |
|---|---|---|
| `scouter-data` | No | None (tool-only) |
| `scouter-briefs` | No | Leader (4b) |
| `scouter-actions` | **Yes** | Executor (9b) / Reviewer (27b) |
| `scouter-mail` | No | None |
| `scouter-browser` | No | None |
| `scouter-notifications` | Yes (resolve) | None |
| `scouter-whatsapp` | No | None |

### Prompt Structure

All prompts live in `app/llm/prompts.py` (606 lines) as Python constants:
- `*_SYSTEM`: System prompt template
- `*_DATA`: User prompt template with `{variable}` placeholders
- Rendered via `PromptDefinition.render_user_prompt(**kwargs)`
- All in Spanish (Argentina)

### What's Missing

| Gap | Impact |
|---|---|
| No per-role identity files | Executor/Reviewer have no documented personality or decision criteria |
| No tool registry documentation | 55 tools undocumented outside code |
| No agent state machine docs | Turn flow, confirmation gates only in code |
| MODEL_ROUTING.md not enforced | Documentation says rules but code doesn't validate against them |
| No skill versioning | No way to track skill evolution |
| No instruction hierarchy docs | Unclear precedence when SOUL.md vs hardcoded prompt conflict |

---

## 6. Communication and Handoff Audit

### Current Communication Mechanisms

| Mechanism | Type | Where Used |
|---|---|---|
| Celery `.delay()` chains | Async task dispatch | Workers → Workers |
| Database writes | State persistence | All services → DB |
| Redis flags | Control signals (stop) | Operator → Workers |
| Notification emitters | One-way events | Services → Notification service |
| Direct function calls | Sync in-process | Service → Service |

### What Does NOT Exist

- **No inter-agent messages** — models don't communicate; they read DB state
- **No handoff notes** — when Executor finishes and Reviewer starts, there's no "here's what I did and why"
- **No feedback from Reviewer to Executor** — review verdicts are stored but never fed back
- **No conversation between roles** — each invocation is stateless and isolated
- **No event bus** — no pub/sub, no Kafka, no RabbitMQ beyond Celery
- **No agent-to-agent threads** — no per-lead discussion trail

### Pipeline Handoff Map

```
task_enrich_lead ──.delay()──→ task_score_lead ──.delay()──→ task_analyze_lead
                                                                    │
                                                          ┌─────────┴─────────┐
                                                     quality=="high"     quality!="high"
                                                          │                   │
                                                   task_research_lead    task_generate_draft
                                                          │                   │
                                                   task_generate_brief        ✓ DONE
                                                          │
                                                   task_review_brief
                                                          │
                                                   task_generate_draft
                                                          │
                                                          ✓ DONE
```

Each arrow is a bare `.delay(lead_id, pipeline_run_id, correlation_id)`. No metadata, no context, no instructions from the previous step. Each task re-fetches the lead from DB and starts fresh.

### Batch Pipeline Exception

Batch mode (`task_batch_pipeline`) runs everything **inline** — no `.delay()` calls. This is more efficient but means there's no per-step tracking granularity in batch mode.

---

## 7. Memory and Learning Audit

### Current State: **ZERO persistent memory or learning**

| Memory Type | Exists? | Details |
|---|---|---|
| Conversation memory | Partial | Mote loads last 50 messages per conversation |
| Per-lead memory | No | Each pipeline run starts fresh |
| Per-vertical memory | No | No industry-specific learning |
| Per-territory memory | No | No geographic learning |
| Pattern memory | No | No signal/outcome correlation storage |
| Feedback storage | No | Review verdicts stored but never aggregated |
| A/B testing | No | No draft variation tracking |
| Outcome tracking | Partial | Lead status lifecycle exists but not correlated to AI decisions |
| Model performance | No | LLMInvocation table has latency/status but no quality metrics |

### What Data Exists But Isn't Used for Learning

1. **LLMInvocation table** — Every invocation logged with status, model, latency, fallback. Could measure model reliability but isn't aggregated.

2. **OutreachLog** — Every draft generation, review, send logged. Could correlate draft quality to outcomes but isn't.

3. **Lead status lifecycle** — NEW → ENRICHED → SCORED → ... → WON/LOST. Could correlate scoring accuracy to conversion but isn't.

4. **Reviewer verdicts** — Every review stores verdict + reasoning. Could feed back to Executor prompts but doesn't.

5. **Inbound classification** — 10 label categories with model attribution. Could measure classifier accuracy but doesn't.

### What the System Forgets

- Which signals predicted HIGH leads that actually converted
- Which outreach angles got replies vs silence
- Which industries respond better to email vs WhatsApp
- Which reviewer corrections are most common
- Which budget tiers were accurate vs wildly off
- Which draft tones convert by vertical
- What research findings actually improved briefs

---

## 8. Feedback Loops and Maturation Audit

### Current Feedback Loops: **None**

The system operates as a **stateless pipeline**. Each lead goes through the same process regardless of what happened to the previous 1,000 leads. There is no mechanism for:

1. **Outcome feedback** — When a lead converts (WON) or fails (LOST), nothing feeds back to the models
2. **Reviewer-to-Executor feedback** — Review verdicts are stored but never influence future Executor prompts
3. **Human-to-system feedback** — When an operator rejects a draft, the rejection reason isn't aggregated
4. **Cross-pipeline learning** — Pipeline N doesn't inform Pipeline N+1
5. **Agent maturation** — No confidence scores, no accuracy tracking, no behavioral adaptation

### The Gap in Numbers

- **237 tests** cover functional correctness but none cover learning or adaptation
- **43 operational settings** control the system but none adapt automatically
- **13 prompt definitions** are static — same prompt for lead #1 and lead #10,000
- **6 Celery queues** process work but none feed back results

---

## 9. Dashboard / AI Office Gaps

### Current Agent Visibility

| Page | What's Visible | Agent Attribution |
|---|---|---|
| `/activity` | Real-time task steps with ModelBadge (27B/9B) | **Best** — shows which model ran each step |
| `/responses` | Inbound classification model + role | **Good** — generator_role · generator_model |
| `/settings` | LLM model config, feature toggles | Config only |
| `/panel` | System health, pipeline controls | No agent info |
| `/leads/[id]` | Task IDs, pipeline status | No model attribution |
| All other pages | No agent information | None |

### What's Missing for AI Office

| Capability | Current | Needed |
|---|---|---|
| Agent hierarchy view | None | Visual org chart showing roles, models, responsibilities |
| Agent communication log | None | Timeline of handoffs with context |
| Decision transparency | None | Why was this lead rated HIGH? Why this contact method? |
| Confidence scores | None | How confident was the classifier? The quality evaluator? |
| Agent performance metrics | None | Accuracy, latency, approval rate per model |
| Memory/learning view | None | What has the system learned? What patterns detected? |
| Feedback dashboard | None | Reviewer corrections aggregated, common issues |
| Pipeline trace | Partial (steps) | Full DAG with model attribution and decision rationale |
| Cost/resource attribution | None | Per-model VRAM, latency, task count |

### TypeScript Types That Already Support Attribution

Some types already have model fields (good foundation):
- `InboundMessage.classification_model`, `classification_role`
- `ReplyAssistantDraft.generator_role`, `generator_model`
- `ReplyAssistantDraftReview.reviewer_model`, `reviewer_role`
- `CommercialBrief.generator_model`, `reviewer_model`
- `LeadResearchReport.researcher_model`
- `ChatMessage.model`

But `TaskStatusRecord` and `OutreachDraft` lack model attribution entirely.

---

## 10. High Lead Premium Lane Audit

### Current HIGH Lane Flow

```
Lead scores HIGH (Executor 9b)
  → Research: HTTP crawl + signal extraction (no LLM)
  → Dossier: LLM structured analysis (Executor 9b)
  → Commercial Brief: LLM opportunity analysis (Executor 9b)
    - opportunity_score, budget_tier, contact_method, call_reason
  → Brief Review: LLM quality check (Reviewer 27b)
  → Draft Generation: Email or WhatsApp (Executor 9b)
    - Conditioned on brief's recommended_contact_method
  → Human approval → Send
```

### What Makes HIGH Leads "Premium" Today

1. **Extra research** — Website crawl with signal detection (SSL, mobile, SEO, custom domain)
2. **Dossier** — Structured business analysis report
3. **Commercial brief** — Budget estimation, opportunity scoring, contact strategy
4. **Brief review** — Reviewer model validates brief quality
5. **Contact method recommendation** — Call vs email vs WhatsApp based on brief analysis

### What's Weak

1. **Research is HTTP-only** — No Playwright, no JavaScript rendering, no deep analysis
2. **No competitive intelligence** — No market/competitor analysis
3. **Dossier is shallow** — Based only on homepage HTML metadata
4. **Brief uses static pricing** — No learning from actual deal outcomes
5. **Contact method is a guess** — No historical data on what works per vertical
6. **No special draft quality** — Same prompt template for HIGH and LOW leads
7. **No post-send tracking** — Can't correlate brief quality to conversion
8. **Review is terminal** — Reviewer feedback doesn't improve next brief

### What Would Make HIGH Truly Premium

- Deep research with Playwright (JS rendering, screenshots, tech stack detection)
- Historical context: "leads like this in [industry] converted at X%"
- Personalized outreach conditioned on research findings + conversion patterns
- Reviewer feedback aggregated into prompt improvements
- Outcome tracking: which briefs led to meetings/conversions

---

## 11. Proposal-to-Agent-System Gap List

| Proposal Vision | Current Reality | Gap Severity |
|---|---|---|
| Agents with clear hierarchy | 1 agent + 3 stateless models | **Critical** |
| Agents that communicate | DB writes only | **Critical** |
| Agents that learn from outcomes | Zero learning | **Critical** |
| Visible AI Office in dashboard | Scattered attribution | **High** |
| Feedback loops and maturation | None | **High** |
| Per-agent memory | Mote: 50 msgs. Others: nothing | **High** |
| Skills per agent | Only Mote has skills | **Medium** |
| Agent meetings and retros | Not possible today | **Medium** |
| Governance framework | Strong for Mote, none for pipeline | **Medium** |
| Outcome-based improvement | Status lifecycle exists, unused | **Medium** |

---

## 12. Recommended Agent Architecture

### Proposed Four-Layer Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    LAYER D: GOVERNANCE                           │
│  Approval gates · Role boundaries · Audit trail · Human veto    │
├──────────────────────────────────────────────────────────────────┤
│                    LAYER C: SYNTHESIS                            │
│  Meeting orchestrator · Report generator · Rule proposals        │
├──────────────────────────────────────────────────────────────────┤
│                    LAYER B: RUNTIME MEMORY                       │
│  Per-agent journals · Per-lead threads · Outcome correlation     │
│  Pattern detection · Feedback aggregation                        │
├──────────────────────────────────────────────────────────────────┤
│                    LAYER A: AGENT IDENTITY                       │
│  Role definitions · Decision policies · Skills · Playbooks       │
└──────────────────────────────────────────────────────────────────┘
```

### Proposed Agent Hierarchy

```
Mote (hermes3:8b) — Chief Intelligence Officer
  ├── Strategy: receives consolidated reports, proposes rule changes
  ├── Interface: human-facing chat across channels
  └── Oversight: reviews agent performance summaries

Analyst (qwen3.5:9b) — Executor Role, Elevated to Agent
  ├── Lead evaluation (quality, summary, angle)
  ├── Research analysis (dossier, signals)
  ├── Brief generation (opportunity, budget, contact)
  └── Draft generation (email, WhatsApp)

Reviewer (qwen3.5:27b) — Quality Assurance Agent
  ├── Lead review
  ├── Draft review
  ├── Brief review
  └── Feedback generation (corrections → Analyst learning)

Coordinator (qwen3.5:4b) — Operational Synthesis
  ├── Daily sync reports
  ├── Weekly retro synthesis
  ├── Metric aggregation
  └── Alert triage
```

### What Changes vs Today

| Today | Proposed |
|---|---|
| Executor is a stateless model call | Analyst is an agent with identity, memory, and decision policies |
| Reviewer verdicts are stored and forgotten | Reviewer feedback aggregated and fed back to Analyst prompts |
| Leader (4b) barely used | Coordinator handles synthesis and reporting |
| No inter-agent communication | Structured handoff notes between pipeline steps |
| No learning | Runtime memory layer with outcome correlation |

---

## 13. Recommended MD / Skills Restructure

### Proposed File Structure

```
docs/agents/
  hierarchy.md              # Agent org chart and authority map
  protocols.md              # Communication, handoff, escalation rules
  skills-registry.md        # All skills across all agents
  memory-model.md           # Memory tiers, retention, promotion rules
  feedback-loops.md         # Outcome → learning → improvement cycle
  governance.md             # What requires approval, audit requirements

docs/agents/mote/
  identity.md               # ← Move SOUL.md + IDENTITY.md content here
  decision-policy.md        # When to confirm, when to proceed, limits
  skills.md                 # Mote-specific skill registry
  
docs/agents/analyst/
  identity.md               # Role, tone, decision criteria
  decision-policy.md        # Quality thresholds, fallback rules
  skills.md                 # Analysis, draft, brief skills
  
docs/agents/reviewer/
  identity.md               # Role, standards, review criteria
  review-policy.md          # What to check, severity levels
  feedback-format.md        # How to structure corrections
  
docs/agents/coordinator/
  identity.md               # Role, synthesis responsibilities
  report-templates.md       # Daily sync, weekly retro formats
  meeting-agenda.md         # Structured meeting templates
```

### What Should Be Runtime-Loaded vs Documentation

| Type | Storage | Loaded By |
|---|---|---|
| Agent identity + personality | `docs/agents/{name}/identity.md` | `prompts.py` at invocation |
| Decision policies | `docs/agents/{name}/decision-policy.md` | Injected into system prompt |
| Review policies | `docs/agents/reviewer/review-policy.md` | Injected into reviewer prompt |
| Hierarchy and protocols | `docs/agents/hierarchy.md`, `protocols.md` | Documentation only |
| Skills registry | `docs/agents/skills-registry.md` | Documentation only |
| Runtime learnings | DB tables (not .md files) | Queried at invocation time |
| Meeting reports | `docs/reports/` (generated) | Read by Mote/Coordinator |

### Key Principle: Canonical .md Files Are NOT Auto-Updated

Following the brief's three-tier model:
1. **Canonical files** (identity, policy, hierarchy) — human/Mote approval required to change
2. **Runtime memory** (learnings, patterns, journals) — stored in DB, auto-updated by agents
3. **Generated reports** (daily syncs, retros, council minutes) — auto-generated, delivered to Mote

---

## 14. Recommended Communication Protocols

### Handoff Protocol

Every pipeline handoff should include a **HandoffNote** (new DB model):

```python
class HandoffNote(Base):
    id: UUID
    pipeline_run_id: UUID
    from_step: str          # "analyze_lead"
    to_step: str            # "research_lead"
    from_role: LLMRole      # EXECUTOR
    to_role: LLMRole        # EXECUTOR
    context: JSON           # what I did, what I found, what to focus on
    confidence: float       # 0.0-1.0
    created_at: datetime
```

This gives the next step context about what happened before — not just raw DB state.

### Feedback Protocol

Every Reviewer invocation should produce a **ReviewFeedback** record:

```python
class ReviewFeedback(Base):
    id: UUID
    review_type: str        # "lead_review", "draft_review", "brief_review"
    target_id: UUID         # lead_id or draft_id
    verdict: str            # "approved", "rejected", "needs_improvement"
    corrections: JSON       # specific issues found
    pattern_tags: list[str] # reusable pattern identifiers
    severity: str           # "minor", "moderate", "critical"
    created_at: datetime
```

Aggregated periodically to detect repeated patterns → inform prompt improvements.

### Meeting Protocol

Structured synthesis events triggered by schedule or lead volume:

| Meeting | Trigger | Participants | Output |
|---|---|---|---|
| Daily Sync | Daily or every N pipelines | Coordinator (synthesizes) | `docs/reports/daily-agent-sync-YYYY-MM-DD.md` |
| Weekly Retro | Weekly | All roles (async) | `docs/reports/weekly-agent-retro-YYYY-MM-DD.md` |
| HIGH Lead Council | Per HIGH batch | Analyst + Reviewer | `docs/reports/high-lead-council-YYYY-MM-DD.md` |
| Strategy Brief | Weekly | Coordinator → Mote | `docs/reports/hermes-strategy-brief-YYYY-MM-DD.md` |

Each meeting is a **Celery task** that queries recent data, runs through Coordinator (4b) for synthesis, and produces a structured report.

---

## 15. Recommended Memory Model

### Three-Tier Memory Architecture

#### Tier 1: Working Memory (per-invocation)
- **Scope**: Single LLM call
- **Content**: System prompt + current lead data + handoff notes
- **Lifetime**: One invocation
- **Storage**: In-memory (prompt construction)
- **Already exists**: Yes (prompt templates + DB reads)

#### Tier 2: Operational Memory (per-agent, persistent)
- **Scope**: Agent-specific learnings across pipelines
- **Content**: Pattern observations, common errors, successful approaches
- **Lifetime**: Weeks/months, with decay
- **Storage**: New DB table `AgentMemory`
- **Does NOT exist today**

```python
class AgentMemory(Base):
    id: UUID
    agent_role: LLMRole
    memory_type: str        # "pattern", "correction", "success", "failure"
    category: str           # "industry", "signal", "draft_tone", "contact_method"
    content: str            # the learning
    confidence: float       # strength of evidence
    evidence_count: int     # how many times observed
    last_reinforced: datetime
    created_at: datetime
```

#### Tier 3: Institutional Memory (system-wide)
- **Scope**: Cross-agent, cross-pipeline insights
- **Content**: Conversion patterns, vertical performance, seasonal trends
- **Lifetime**: Permanent (with versioning)
- **Storage**: New DB table `SystemInsight` + periodic report files
- **Does NOT exist today**

### Memory Injection Strategy

At invocation time, inject relevant Tier 2 memories into the system prompt:

```python
def build_analyst_prompt(lead: Lead, memories: list[AgentMemory]) -> str:
    base_prompt = LEAD_QUALITY_SYSTEM
    if memories:
        memory_block = "\n## Learned Patterns\n"
        for m in memories[:5]:  # top 5 by confidence
            memory_block += f"- {m.content} (seen {m.evidence_count}x)\n"
        base_prompt += memory_block
    return base_prompt
```

### What to Learn (Priority Order)

1. **Signal → Quality correlation** — Which signals predict HIGH leads that actually convert?
2. **Draft → Response correlation** — Which tones/angles get replies?
3. **Industry → Channel correlation** — Which verticals respond to email vs WhatsApp?
4. **Reviewer corrections** — What errors repeat? Feed back to Executor prompts.
5. **Budget accuracy** — Were budget tier predictions close to actual deals?
6. **Research value** — Which research signals improved brief quality?

---

## 16. Recommended Feedback / Learning Loops

### Loop 1: Reviewer → Analyst (Short-cycle)

```
Analyst generates draft/brief
  → Reviewer evaluates → ReviewFeedback record
  → Aggregator (daily) groups by pattern_tags
  → If pattern seen ≥3 times:
      → Create AgentMemory for Analyst
      → Inject into Analyst's next invocation
```

**Impact**: Analyst improves based on Reviewer's corrections within days.

### Loop 2: Outcome → System (Medium-cycle)

```
Lead reaches WON/LOST status
  → Outcome Tracker correlates:
      - signals at enrichment
      - quality rating at analysis
      - brief predictions (budget, channel)
      - draft content/tone
  → Pattern Detector identifies:
      - signal combos that predict WON
      - draft approaches that get replies
      - contact methods that work per vertical
  → SystemInsight created
  → Injected into relevant prompts
```

**Impact**: System gets smarter about what works, across all leads.

### Loop 3: Human → Agent (Continuous)

```
Operator rejects draft → reason stored
Operator approves modified draft → diff stored
Operator changes contact method → preference stored
  → Feedback Aggregator groups by type
  → Operator Preference Memory created
  → Injected into Mote's context + Analyst's prompts
```

**Impact**: System adapts to operator style and preferences.

### Loop 4: Synthesis → Strategy (Long-cycle)

```
Weekly:
  → Coordinator synthesizes all memories + metrics
  → Produces strategy brief for Mote
  → Mote reviews and can:
      - Approve prompt modifications (canonical file changes)
      - Flag issues for human review
      - Propose new skills or rule changes
```

**Impact**: System evolves its own operating procedures over time.

---

## 17. Implementation Priorities

### Phase 0: Foundation (1-2 weeks)
- [ ] Create `docs/agents/hierarchy.md` — formalize the real hierarchy
- [ ] Create `docs/agents/protocols.md` — document communication rules
- [ ] Create `docs/agents/skills-registry.md` — inventory all skills
- [ ] Move SOUL.md + IDENTITY.md content into `docs/agents/mote/identity.md` (keep originals as symlinks)
- [ ] Create identity files for Analyst and Reviewer roles

### Phase 1: Handoff Notes (2-3 weeks)
- [ ] Create `HandoffNote` model and migration
- [ ] Modify pipeline tasks to emit handoff notes between steps
- [ ] Inject handoff context into next step's prompt
- [ ] Add handoff visibility to Activity page

### Phase 2: Reviewer Feedback Loop (2-3 weeks)
- [ ] Create `ReviewFeedback` model and migration
- [ ] Modify review service to produce structured feedback
- [ ] Create daily aggregation task (Celery Beat)
- [ ] Create `AgentMemory` model and migration
- [ ] Inject top memories into Executor prompts

### Phase 3: Outcome Tracking (2-3 weeks)
- [ ] Create outcome correlation service
- [ ] On WON/LOST status change, correlate to pipeline decisions
- [ ] Create `SystemInsight` model
- [ ] Pattern detection for signal/quality/channel correlations

### Phase 4: Agent Meetings (1-2 weeks)
- [ ] Create meeting orchestration Celery tasks
- [ ] Daily sync report generation (Coordinator/4b)
- [ ] Weekly retro synthesis
- [ ] Report delivery to Mote context

### Phase 5: AI Office Dashboard (3-4 weeks)
- [ ] Agent hierarchy page (`/agents`)
- [ ] Decision log with rationale and confidence
- [ ] Agent performance metrics (accuracy, latency, approval rate)
- [ ] Memory/learning visualization
- [ ] Pipeline trace with model attribution
- [ ] Meeting report viewer

### Phase 6: Outcome-Based Improvement (2-3 weeks)
- [ ] Prompt injection of learned patterns
- [ ] A/B framework for draft variations
- [ ] Vertical-specific learning
- [ ] Automatic prompt version proposals (Mote review required)

---

## 18. Risks / Anti-Patterns

### Risks to Avoid

1. **Memory as noise** — Without quality gates, agent memory becomes garbage. Every memory entry needs confidence scoring and evidence count. Decay unused memories.

2. **Feedback loops that amplify bias** — If the system only learns from approved drafts, it converges to operator style rather than effectiveness. Always correlate to outcomes (replies, conversions), not just approvals.

3. **Overengineered communication** — The brief warns against "agents talking for aesthetics." Handoff notes should be structured data, not free-text conversations. If a handoff note doesn't improve the next step's output, remove it.

4. **Dashboard widget bloat** — Every dashboard addition should answer: "What decision does this help the operator make?" If no clear answer, don't build it.

5. **Canonical file drift** — If agents can propose changes to canonical files, there must be a version control + approval workflow. Never let runtime processes rewrite identity or policy files directly.

6. **Double leadership** — The brief asks "who really leads?" Today the answer is clear: code leads the pipeline, Mote leads the chat. Don't create ambiguity by giving Mote pipeline override authority without careful governance design.

7. **Memory size explosion** — Cap memory tables aggressively. 100 AgentMemory records per role, 500 SystemInsight records total. Prune by confidence × recency.

### Anti-Patterns from the Brief's "What I Don't Want"

| Anti-Pattern | Mitigation |
|---|---|
| "Personality" without impact | Agent identities must change behavior, not just labels |
| Useless .md files | Every .md must be either runtime-loaded or actively referenced |
| Artificial communication | Only build handoffs that improve next-step output quality |
| Chaotic memory | Structured schema, confidence scoring, capped size, decay |
| Aesthetic agents | No dashboard widgets without clear operational value |
| Overengineering | Phase implementation; validate each phase improves metrics before next |
| Duplicated docs/code | Runtime rules in code; docs describe intent and rationale only |
| Confused command | One decision authority per domain; document in hierarchy.md |

---

## 19. Open Questions

1. **Should Mote have pipeline override authority?** Today Mote can trigger pipelines via tools but can't change routing logic. Should Mote be able to say "route this lead to HIGH lane even though it scored MEDIUM"?

2. **Memory storage: DB vs .md files?** The brief suggests both. Recommendation: DB for structured runtime memory (queryable, decayable), .md only for generated reports and canonical docs.

3. **How deep should research go?** Current research is HTTP-only. Playwright integration would significantly improve HIGH lead intelligence but adds complexity and resource requirements.

4. **Meeting frequency vs value?** Daily syncs are valuable early; may become noise once patterns stabilize. Build with configurable frequency from day one.

5. **Should the Reviewer be always-on or on-demand?** Today it's toggled by `reviewer_enabled`. In an Agent OS, should the Reviewer automatically review all HIGH leads, or stay on-demand?

6. **How to handle memory conflicts?** When Reviewer memory says "don't use casual tone" but outcome data says casual tone gets more replies, which wins? Recommendation: outcome data, surfaced for human review.

7. **What's the first metric to optimize?** Conversion rate (WON/total)? Reply rate? Meeting rate? This determines which feedback loop to build first.

8. **How to prevent model VRAM conflicts?** With 4 models potentially active, Ollama may need to swap models frequently. Memory management strategy needed (keep executor warm, load reviewer on demand).

9. **Should canonical .md changes require a PR?** Or is Mote + human approval in dashboard sufficient? Recommendation: start with Mote proposals in reports, human applies via PR.

10. **How to measure if the Agent OS is actually maturing?** Proposed: track a composite "system intelligence score" = f(conversion_rate_delta, reviewer_approval_rate, memory_hit_rate, feedback_incorporation_rate) over monthly windows.
