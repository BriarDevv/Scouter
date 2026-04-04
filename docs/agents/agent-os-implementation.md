# Scouter Agent OS — Implementation Reference

**Status:** Implemented, formalized, and hardened
**Date:** 2026-04-04
**Commits:** 40+ on main
**Tests:** 299 passing
**Audited:** Security (3 HIGH fixed), Architecture (PASS), Quality (8.5/10)
**Docs:** hierarchy, protocols, governance, identities, skills-registry

---

## The Team

```
AGENTS (have loop, tools, decide)
├── Mote (hermes3:8b) — Jefe de operaciones + Closer
└── Scout (qwen3.5:9b) — Investigador de campo con Playwright

MODELS (single-shot, stateless)
├── Executor (qwen3.5:9b) — Genera análisis, briefs, drafts
└── Reviewer (qwen3.5:27b) — Revisa y corrige con feedback estructurado

RESERVED
└── Leader (qwen3.5:4b) — Weekly synthesis (when earned)
```

---

## How It Works

### Pipeline Context Flow

Each step writes findings to `PipelineRun.step_context_json`. Draft generation reads everything.

```
Enrichment → { signals, email_found, website_exists }
    ↓
Scoring → { score, signal_count }
    ↓
Analysis (Executor) → { quality, reasoning, suggested_angle }
    ↓
Scout (9b + tools) → { pages_visited, findings, opportunity }
    ↓
Brief (Executor) → { opportunity_score, budget, channel, angle }
    ↓
Review (Reviewer) → { approved, corrections }
    ↓
Draft (Executor, reads ALL above) → personalized outreach
```

### Three Feedback Loops

1. **Reviewer → Prompts**: Structured corrections stored in `review_corrections` table. Patterns aggregated weekly → prompt improvements.
2. **Outcomes → Scoring**: `outcome_snapshots` captures pipeline state on WON/LOST. Signal correlation → scoring weight adjustments.
3. **Scout → Dossiers**: Deep Playwright research → richer briefs → better drafts.

### Weekly Synthesis

Celery Beat task aggregates 7-day data → LLM synthesis → WeeklyReport. Injected into Mote's system context so Mote can explain insights.

---

## Architecture

### New Models (5)

| Model | Table | Purpose |
|---|---|---|
| ReviewCorrection | `review_corrections` | Structured reviewer feedback (category, severity, issue, suggestion) |
| InvestigationThread | `investigation_threads` | Scout tool call history per lead |
| OutcomeSnapshot | `outcome_snapshots` | Pipeline state frozen on WON/LOST |
| OutboundConversation | `outbound_conversations` | Mote's conversations with clients |
| WeeklyReport | `weekly_reports` | Automated synthesis reports |

### New Services (5)

| Service | Path | Purpose |
|---|---|---|
| context_service | `app/services/pipeline/context_service.py` | Pipeline context read/write/format |
| outcome_tracking_service | `app/services/pipeline/outcome_tracking_service.py` | Capture snapshots on WON/LOST |
| outcome_analysis_service | `app/services/pipeline/outcome_analysis_service.py` | Signal correlation, recommendations |
| auto_send_service | `app/services/outreach/auto_send_service.py` | Mote outreach via WhatsApp/email |
| closer_service | `app/services/outreach/closer_service.py` | Intent detection + response generation |

### Scout Agent

| File | Purpose |
|---|---|
| `app/agent/research_agent.py` | Synchronous agent loop (max 10 loops, 90s timeout) |
| `app/agent/scout_tools.py` | 6 Playwright tools with SSRF protection |
| `app/agent/scout_prompts.py` | Investigation protocol and output format |

**Tools:** browse_page, extract_contacts, check_technical, take_screenshot, search_competitors, finish_investigation

### API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/ai-office/status` | GET | Agent status overview (4 agents) |
| `/ai-office/decisions` | GET | Recent LLM decisions log |
| `/ai-office/investigations` | GET | Scout investigation threads |
| `/ai-office/conversations` | GET | Mote outbound conversations |
| `/ai-office/conversations/{id}` | GET | Full conversation thread |
| `/ai-office/conversations/{id}/takeover` | POST | Operator takes control |
| `/ai-office/conversations/{id}/reply` | POST | Mote generates closer response |
| `/ai-office/conversations/{id}/send-reply` | POST | Send response via WhatsApp |
| `/ai-office/test-send-whatsapp` | POST | Test WhatsApp delivery |
| `/ai-office/weekly-reports` | GET | List weekly reports |
| `/ai-office/weekly-reports/generate` | POST | Trigger manual report |
| `/performance/ai-health` | GET | Approval rate, fallback rate, latency |
| `/performance/outcomes` | GET | WON/LOST by industry, quality, signals |
| `/performance/outcomes/signals` | GET | Signal-to-outcome correlation |
| `/performance/recommendations` | GET | Scoring recommendations from data |
| `/performance/analysis/summary` | GET | Full outcome analysis |
| `/performance/investigations/{id}` | GET | Scout thread for a lead |
| `/reviews/corrections/summary` | GET | Top correction patterns |
| `/pipelines/runs/{id}/context` | GET | Pipeline step context |

### Dashboard

| Component | Location | Shows |
|---|---|---|
| AI Office page | `/ai-office` | Agent status, decisions, investigations, outcomes |
| AiDecisionsPanel | Lead Detail page | Pipeline reasoning, Scout findings, brief, review |
| InvestigationThreadView | Lead Detail page | Scout tool calls (expandable) |
| AiHealthCard | Panel page | Approval rate, fallback rate, latency |
| TopCorrections | Panel page | Reviewer correction patterns |

---

## Configuration

### Low Resource Mode (notebook / no GPU)

```env
LOW_RESOURCE_MODE=true
```

Single Celery queue, concurrency=1, sequential model loading. For machines with ≤16GB RAM.

### Hardware Profiles

| Profile | Config |
|---|---|
| Desktop (4080 16GB, 32GB RAM) | All models, concurrent queues |
| Notebook (Intel Ultra 9, 16GB RAM) | LOW_RESOURCE_MODE=true |

---

## Security

Addressed in security audit (2026-04-04):

| Fix | Location |
|---|---|
| SSRF protection (private IP blocking) | `scout_tools.py` — `_validate_url()` |
| Prompt injection mitigation | `closer_service.py` — `_sanitize_client_message()` |
| WhatsApp endpoint hardening | `ai_office.py` — phone validation, message length cap |
| Context size limits | `context_service.py` — 2KB/step, 16KB total |

---

## Migrations

```
g1a2b3c4d5e6 — step_context_json + review_corrections
h2b3c4d5e6f7 — investigation_threads + outcome_snapshots
i3c4d5e6f7g8 — outbound_conversations
j4d5e6f7g8h9 — weekly_reports
```

Run: `.venv/bin/python3 -m alembic upgrade head`

---

## Current State (2026-04-04)

**Tests:** 299 passing (291 backend + 8 AI Office endpoints)
**Docs:** 5 canonical Agent OS docs (hierarchy, protocols, governance, identities, skills-registry)

### Closed since initial implementation

- [x] Tests for Agent OS services (56 new tests: context, closer, outcomes, auto_send, weekly, ai-office)
- [x] Move closer prompt to prompt_registry
- [x] Kapso Cloud API rewrite (WhatsApp Business Cloud API via proxy)
- [x] Template-first WhatsApp flow (template opens conversation, draft on reply)
- [x] Template selection by lead signals
- [x] Expanded onboarding (WhatsApp + Telegram + brand + outreach channel required)
- [x] Security: phone from query param to POST body
- [x] Silent except-pass replaced with structured logging
- [x] Proxy path allowlist + traversal guard
- [x] ReadinessGate wired into layout

### Next Steps

See [whatsapp-outreach-strategy.md](whatsapp-outreach-strategy.md) for the template-based outreach plan.
See [hierarchy.md](hierarchy.md), [protocols.md](protocols.md), [governance.md](governance.md) for Agent OS docs.

### Remaining Backlog

- [ ] Tailwind dynamic class fix (use lookup maps)
- [ ] Replace Google HTML scraping with search API
- [ ] Populate OutcomeSnapshot.reviewer_verdict
- [ ] Create WhatsApp templates in Kapso panel + get Meta approval
- [ ] Implement Kapso webhook receiver for inbound client replies
- [ ] Test full template→reply→closer flow end-to-end with real WhatsApp
