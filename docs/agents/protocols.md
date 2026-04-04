# Agent OS Protocols

**Status:** Current as of 2026-04-04

## Communication Protocol

Agents do NOT talk to each other directly. All communication is through structured data:

### Pipeline Context Flow (step_context_json)

```
Enrichment → { signals, email_found, website_exists }
    ↓ written to PipelineRun.step_context_json["enrichment"]
Scoring → { score, signal_count }
    ↓ written to step_context_json["scoring"]
Analysis (Executor) → { quality, reasoning, suggested_angle }
    ↓ written to step_context_json["analysis"]
Scout (9b + tools) → { pages_visited, findings, opportunity }
    ↓ written to step_context_json["scout"]
Brief (Executor) → { opportunity_score, budget, channel, angle }
    ↓ written to step_context_json["brief"]
Review (Reviewer) → { approved, corrections }
    ↓ written to step_context_json["brief_review"]
Draft (Executor, reads ALL above) → personalized outreach
```

Each step writes via `context_service.append_step_context()`.
Downstream steps read via `context_service.get_step_context()`.
Draft generation reads everything via `format_context_for_prompt()`.

### Size Limits

- Max 2KB per step
- Max 16KB total per pipeline run
- Truncation to `{truncated: true, summary: "..."}` if exceeded

## Feedback Loops

### 1. Reviewer → Prompts

```
Reviewer output → structured corrections (category, severity, issue, suggestion)
    ↓ persisted to review_corrections table
    ↓ aggregated weekly
    ↓ top patterns → prompt improvement recommendations
    ↓ operator decides whether to apply
```

Categories: tone, cta, personalization, length, accuracy, relevance, format, language
Severities: critical, important, suggestion

### 2. Outcomes → Scoring

```
Lead status → WON or LOST
    ↓ capture_outcome_snapshot() freezes pipeline state
    ↓ signal correlation analysis (which signals predict WON?)
    ↓ quality accuracy analysis (were HIGH leads actually good?)
    ↓ industry performance (which industries convert?)
    ↓ scoring recommendations (gated at ≥50 outcomes)
```

### 3. Scout → Dossiers

```
Scout investigation → InvestigationThread (tool calls, pages, findings)
    ↓ written to step_context_json["scout"]
    ↓ enriches brief generation
    ↓ enriches draft personalization
    ↓ visible in AI Office dashboard
```

## WhatsApp Outreach Protocol

```
1. Pipeline completes → draft approved → template selected by signals
2. Template sent via Kapso Cloud API (opens WhatsApp conversation)
3. Client responds → 24h window opens
4. Mote sends personalized draft (queued from step 1)
5. Closer mode: Mote handles conversation using lead context
6. Operator can takeover at any point via /ai-office/conversations/{id}/takeover
```

## Weekly Synthesis

```
Celery Beat (Sunday 20:00 ART) → task_weekly_report
    ↓ collect metrics (leads, outcomes, invocations, corrections, investigations)
    ↓ collect recommendations from outcome_analysis_service
    ↓ generate synthesis (LLM or template fallback)
    ↓ store WeeklyReport
    ↓ inject into Mote's system context (max 500 chars)
```

## Error Handling

| Situation | Behavior |
|-----------|----------|
| Executor fails | Fallback to heuristic values (quality=unknown, etc) |
| Reviewer fails | Skip review, mark as degraded |
| Scout fails | Fall back to HTTP research (httpx), skip Playwright |
| Closer LLM fails | Return error, suggest operator takeover |
| Weekly synthesis LLM fails | Fall back to template synthesis |
| Kapso fails | Mark conversation as closed with error |
