---
name: scouter-data
description: "Exact grounded data from Scouter. Exec: cd /home/briar/src/Scouter && .venv/bin/python scripts/scouterctl.py --data-only --compact <cmd>. Commands: ops-overview | ops-top-leads --limit N | ops-replies-summary --hours N | ops-important-replies --limit N | positive-replies | quote-replies | meeting-replies | ops-recent-drafts --limit N | drafts-ready | recent-pipelines | task-health | running-tasks | failed-tasks | activity --limit N | ops-settings-llm | performance-summary. Return ONLY the JSON output."
metadata: { "hermes": { "emoji": "📊", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# Scouter Data Skill

Scouter is the source of truth. This skill returns exact data via grounded wrappers.

## When to use

- Exact counts, IDs, statuses, lists, model names
- "cuántos leads hay", "qué replies llegaron", "qué drafts están pendientes"
- Any question that needs a precise number or list

## When NOT to use

- Summaries, prioritization, next-step suggestions → use **scouter-briefs**
- Sending drafts, delivery status → use **scouter-mail**
- Website inspection → use **scouter-browser**
- Generate draft, run pipeline, request review → use **scouter-actions**
- Notifications, alerts → use **scouter-notifications**

## Hard rules

1. Do not answer from memory.
2. Execute exactly one wrapper command first.
3. Final answer = wrapper JSON only. No markdown fences. No commentary.
4. If wrapper errors, return only the error JSON.
5. Never read workspace files (AGENTS.md, SOUL.md, etc.) for data queries.

## Commands

```bash
cd /home/briar/src/Scouter && .venv/bin/python scripts/scouterctl.py --data-only --compact <command> [args]
```

| Request | Command |
|---|---|
| Overview numbers | `ops-overview` |
| Top/best leads | `ops-top-leads --limit <n>` |
| Reply summary / inbox counts | `ops-replies-summary --hours <n>` |
| Important replies | `ops-important-replies --limit <n> --hours <n>` |
| Positive replies | `positive-replies --limit <n> --hours <n>` |
| Quote requests | `quote-replies --limit <n> --hours <n>` |
| Meeting requests | `meeting-replies --limit <n> --hours <n>` |
| Reviewer candidates | `reviewer-candidates --limit <n> --hours <n>` |
| Recent drafts | `ops-recent-drafts --limit <n>` |
| Drafts ready to send | `drafts-ready --limit <n>` |
| Recent pipelines | `recent-pipelines --limit <n>` |
| Task health | `task-health --limit <n>` |
| Running tasks | `running-tasks --limit <n>` |
| Failed tasks | `failed-tasks --limit <n>` |
| Activity log | `activity --limit <n>` |
| LLM model settings | `ops-settings-llm` |
| Performance summary | `performance-summary` |

Never derive counts from filtered lists. Use the appropriate command directly.
