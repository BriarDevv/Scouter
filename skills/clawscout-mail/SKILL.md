---
name: clawscout-mail
description: "Mail operations. Exec: cd /home/briar/src/ClawScout && .venv/bin/python scripts/mailctl.py --data-only --compact <cmd>. Commands: recent-drafts --limit N | draft-detail --draft-id ID | send-status --draft-id ID | send-draft --draft-id ID. Return ONLY the JSON output."
metadata: { "openclaw": { "emoji": "✉️", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Mail Skill

Send approved drafts and check delivery status. Uses mailctl.py for grounded mail operations.

## When to use

- "qué drafts están aprobados para enviar?"
- "mandá el draft X"
- "qué pasó con el envío del draft X?"

## When NOT to use

- Generating new drafts → use **clawscout-actions**
- Reviewing drafts → use **clawscout-actions**
- Listing all drafts (not mail-specific) → use **clawscout-data**
- Reply assisted drafts → use **clawscout-actions**

## Hard rules

1. Execute exactly one wrapper command first.
2. Final answer = wrapper JSON only. No markdown fences.
3. Sending requires explicit user intent. Never send multiple unless user clearly scopes it.

## Commands

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/mailctl.py --data-only --compact <command> [args]
```

| Request | Command |
|---|---|
| Recent approved drafts | `recent-drafts --limit <n>` |
| Draft detail | `draft-detail --draft-id <id>` |
| Delivery status | `send-status --draft-id <id>` |
| Send one draft | `send-draft --draft-id <id>` |
