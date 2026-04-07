---
name: scouter-mail
description: "Mail operations. Exec: source .venv/bin/activate && python scripts/mailctl.py --data-only --compact <cmd>. Commands: recent-drafts --limit N | draft-detail --draft-id ID | send-status --draft-id ID | send-draft --draft-id ID. Return ONLY the JSON output."
metadata: { "hermes": { "emoji": "✉️", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# Scouter Mail Skill

Send approved drafts and check delivery status. Uses mailctl.py for grounded mail operations.

## When to use

- "qué drafts están aprobados para enviar?"
- "mandá el draft X"
- "qué pasó con el envío del draft X?"

## When NOT to use

- Generating new drafts → use **scouter-actions**
- Reviewing drafts → use **scouter-actions**
- Listing all drafts (not mail-specific) → use **scouter-data**
- Reply assisted drafts → use **scouter-actions**

## Hard rules

1. Execute exactly one wrapper command first.
2. Final answer = wrapper JSON only. No markdown fences.
3. Sending requires explicit user intent. Never send multiple unless user clearly scopes it.

## Commands

```bash
source .venv/bin/activate && python scripts/mailctl.py --data-only --compact <command> [args]
```

| Request | Command |
|---|---|
| Recent approved drafts | `recent-drafts --limit <n>` |
| Draft detail | `draft-detail --draft-id <id>` |
| Delivery status | `send-status --draft-id <id>` |
| Send one draft | `send-draft --draft-id <id>` |
