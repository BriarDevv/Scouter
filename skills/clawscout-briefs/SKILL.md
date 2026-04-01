---
name: clawscout-briefs
description: "Operational briefs and prioritization. Exec: cd /home/briar/src/ClawScout && .venv/bin/python scripts/opsctl.py --compact <cmd>. Commands: replies-digest --hours N | important-replies-brief --hours N | leads-priority --limit N | commercial-brief --hours N | settings-brief. Summarize the JSON output in Spanish."
metadata: { "hermes": { "emoji": "📋", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Briefs Skill

Operational briefs that run grounded wrappers first, then ask the leader model to summarize.

## When to use

- "resumime los replies importantes"
- "qué leads debería mirar primero"
- "qué drafts parecen más urgentes"
- "qué cambió hoy en el inbox comercial"
- "resumime el estado operativo"
- Any question asking for prioritization or next-step suggestions

## When NOT to use

- Exact counts, IDs, raw lists → use **clawscout-data**
- Sending drafts → use **clawscout-mail**
- Mutating actions → use **clawscout-actions**

## Hard rules

1. Do not improvise tool calls — use `opsctl.py` which handles tool-first + leader-after.
2. Do not restate counts or IDs not present in the returned JSON.
3. If the user wants raw exact numbers, redirect to **clawscout-data** instead.
4. Model: leader (qwen3.5:4b)

## Commands

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/opsctl.py --compact <command> [args]
```

| Request | Command |
|---|---|
| Replies digest | `replies-digest --hours <n> --limit <n>` |
| Important replies brief | `important-replies-brief --hours <n> --limit <n>` |
| Leads priority | `leads-priority --limit <n> --drafts-limit <n>` |
| Commercial brief | `commercial-brief --hours <n> --limit <n> --drafts-limit <n>` |
| Settings brief | `settings-brief` |
