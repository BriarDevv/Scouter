---
name: clawscout-mail
description: "Use ClawScout mail wrappers for exact draft lookup, delivery status, and explicit single-draft sends."
metadata: { "openclaw": { "emoji": "✉️", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Mail Skill

ClawScout is the source of truth for drafts and deliveries.

Use this skill only for:

- recent drafts
- draft detail
- delivery status for one draft
- sending one explicit approved draft

Do not use this skill for:

- reply summaries
- reply prioritization
- top leads
- model/settings questions
- SMTP direct access

## Hard rule for exact draft queries

For exact draft or delivery data:

1. Do not explain the plan.
2. Do not inspect files if the wrapper exists.
3. Execute exactly one wrapper command first.
4. Final answer must be only the wrapper JSON.
5. Do not use Markdown fences.

Commands:

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/mailctl.py --data-only --compact recent-drafts --limit <n>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/mailctl.py --data-only --compact draft-detail --draft-id <draft_id>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/mailctl.py --data-only --compact send-status --draft-id <draft_id>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/mailctl.py --data-only --compact send-draft --draft-id <draft_id>
```

Sending requires explicit user intent. Never send multiple drafts unless the user clearly scopes the request.
