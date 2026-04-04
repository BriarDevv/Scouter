# Agent OS Governance

**Status:** Current as of 2026-04-04

## Runtime Modes

The operator controls how much autonomy the system has:

| Mode | Who sends | What happens |
|------|-----------|-------------|
| `safe` | Human only | Mote suggests, human sends manually |
| `assisted` | Human approves, system sends | Draft approved → auto-sent |
| `outreach` | Mote sends first message | Template sent → waits for reply → human takes over |
| `closer` | Mote manages conversation | Template → reply → personalized draft → full conversation |

Default: `safe`. Changed via operational settings.

## Human Approval Points

| Action | Requires human? | Mode override |
|--------|----------------|---------------|
| Process new leads | No (automatic pipeline) | Always automatic |
| Send outreach draft | Yes in safe/assisted | No in outreach/closer |
| Reply to client | Yes in safe/assisted/outreach | No in closer |
| Accept scoring recommendations | Always yes | No override |
| Modify prompts | Always yes | No override |
| Take over conversation | Always available | All modes |

## LOW_RESOURCE_MODE

For machines with ≤16GB RAM and no dedicated GPU.

**Config:** `LOW_RESOURCE_MODE=true` in `.env`

**Effect:**
- Celery: single `default` queue, concurrency=1
- Models load one at a time (no parallel LLM calls)
- All tasks serialized through single worker
- Reviewer (27b) can be disabled entirely if needed

**Hardware profiles:**

| Profile | Config |
|---------|--------|
| Desktop (4080 16GB, 32GB RAM) | All models, concurrent queues |
| Notebook (Intel Ultra 9, 16GB RAM) | LOW_RESOURCE_MODE=true |

## Security Boundaries

| Boundary | Protection |
|----------|-----------|
| Scout web browsing | SSRF protection: private IP blocking in _validate_url() |
| Client messages in closer | Prompt injection sanitization + `<client_message>` delimiters |
| WhatsApp test endpoint | POST body (not query params), phone validation, message length cap |
| Setup actions | Rate limited (5s cooldown), allowlisted commands only |
| Next.js proxy | Path allowlist, traversal guard, API key server-side only |
| Pipeline context | 2KB/step, 16KB total size limits |
| Command output | Credential stripping, URL sanitization, 2KB cap |

## Observability

All LLM invocations logged to `llm_invocations` table with:
- function_name, prompt_id, prompt_version
- role, model, status (succeeded/degraded/fallback/failed)
- latency_ms, parse_valid, fallback_used
- target_type, target_id, tags

Dashboard visibility:
- `/ai-office` — agent status, decisions, investigations, outcomes
- `/panel` — AI health card, top corrections
- Lead detail — AI decisions panel, investigation thread
