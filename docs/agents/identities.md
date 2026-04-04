# Agent Identities

**Status:** Current as of 2026-04-04

---

## Mote — Jefe de operaciones + Closer

**Model:** hermes3:8b
**Type:** Agent (loop + tools + decisions)
**Files:** SOUL.md, IDENTITY.md, app/agent/core.py

**Identity:**
Mote is the operator-facing AI assistant. Speaks rioplatense Spanish, is direct
and conversational. Has access to 55 tools covering the full Scouter workflow.

**Responsibilities:**
- Answer operator questions about leads, pipeline, metrics
- Execute operator commands (process leads, send drafts, check status)
- In closer mode: maintain WhatsApp conversations with potential clients
- Explain weekly report insights when asked
- Escalate to human when conversation gets complicated or client objects

**Context injection:**
- Latest WeeklyReport synthesis (max 500 chars) in system context
- Lead + brief + pipeline context when in closer mode
- Conversation history (last 10 messages) in closer mode

**Limitations:**
- Cannot modify scoring weights or prompts
- Cannot send messages in safe/assisted mode without approval
- Stateless: no memory between conversations (context from DB only)

---

## Scout — Investigador de campo

**Model:** qwen3.5:9b
**Type:** Agent (synchronous loop in Celery task)
**Files:** app/agent/research_agent.py, app/agent/scout_tools.py, app/agent/scout_prompts.py

**Identity:**
Scout is a research specialist that deeply investigates leads using Playwright
browser automation. Runs as a synchronous agent loop inside a Celery task.

**Responsibilities:**
- Visit lead's website, Instagram, social profiles
- Extract contacts, check technical quality (SSL, mobile, SEO, speed)
- Find competitors in the same industry and city
- Produce structured findings for downstream brief generation

**Constraints:**
- Max 10 tool call loops per investigation
- 90 second timeout
- SSRF protection: private IPs blocked
- Falls back to HTTP research if Playwright unavailable
- Findings stored in InvestigationThread and step_context_json

---

## Executor — Generador

**Model:** qwen3.5:9b
**Type:** Model (single-shot, stateless)
**Files:** app/llm/client.py, app/llm/invocations/

**Identity:**
Executor is the workhorse that generates all analytical content: business
summaries, quality evaluations, commercial briefs, outreach drafts, and
weekly synthesis. Always uses structured JSON output.

**Responsibilities:**
- Evaluate lead quality (high/medium/low with reasoning)
- Generate commercial briefs with opportunity scores
- Write personalized outreach drafts using full pipeline context
- Generate weekly team synthesis reports

**Constraints:**
- Stateless: receives all context in the prompt, no memory
- Output validated against Pydantic schemas
- Degraded mode: heuristic fallback extracts JSON from dirty output
- Fallback mode: returns default values when LLM completely fails

---

## Reviewer — Revisor

**Model:** qwen3.5:27b
**Type:** Model (single-shot, stateless)
**Files:** app/llm/client.py, app/services/review_service.py

**Identity:**
Reviewer is the quality gate. Uses a larger model (27b) to evaluate and
correct the work of the Executor (9b). Outputs structured corrections
that feed the improvement loop.

**Responsibilities:**
- Review leads: confirm/adjust quality rating
- Review briefs: approve or reject with specific corrections
- Review outreach drafts: check tone, accuracy, personalization
- Classify inbound replies: intent detection for response routing

**Corrections output:**
Each review produces structured corrections:
```json
{"category": "tone", "severity": "important", "issue": "...", "suggestion": "..."}
```
Persisted to `review_corrections` table, aggregated into recommendations.

**Constraints:**
- Larger model = slower, so used only for review steps
- In LOW_RESOURCE_MODE: can be disabled entirely (skip review step)
- Never generates content, only evaluates

---

## Leader — Reserved

**Model:** qwen3.5:4b
**Type:** Reserved (no active role)

The 4b model was reserved for lightweight coordination tasks.
Currently unused — weekly synthesis runs on Executor (9b) instead.
May be activated in the future for:
- Quick triage/routing decisions
- Simple classification tasks
- Lightweight status summaries
