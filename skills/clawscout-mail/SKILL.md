---
name: clawscout-mail
description: "Use ClawScout's local mail wrapper scripts/mailctl.py for grounded draft lookup, delivery status, and explicit single-draft sends. Use this when the user asks to list ready drafts, inspect a draft, send one approved draft, or check the recorded delivery result."
metadata: { "openclaw": { "emoji": "✉️", "always": true, "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Mail Skill

ClawScout remains the source of truth. Always use `scripts/mailctl.py` for mail operations instead of talking to SMTP directly.

## Use this skill for

- Listing recent approved drafts that are candidates to send
- Inspecting one draft by `draft_id`
- Sending one explicit approved draft
- Checking the recorded delivery status for one draft

## Do not use this skill for

- Sending multiple drafts unless the user explicitly asks and the scope is clearly bounded
- Talking directly to SMTP
- Inventing delivery state
- Campaigns, sequences, or follow-ups
- WhatsApp or other channels

## Command map

Run commands from the ClawScout workspace root:

```bash
python3 scripts/mailctl.py recent-drafts --limit 10
python3 scripts/mailctl.py draft-detail --draft-id <draft_id>
python3 scripts/mailctl.py send-status --draft-id <draft_id>
python3 scripts/mailctl.py send-draft --draft-id <draft_id>
```

## Workflow rules

- For "mostrame drafts listos":
  - use `python3 scripts/mailctl.py recent-drafts --limit <n>`
- For "mostrame este draft":
  - use `python3 scripts/mailctl.py draft-detail --draft-id <draft_id>`
- For "enviá este draft":
  - use `python3 scripts/mailctl.py send-draft --draft-id <draft_id>`
- For "qué pasó con este envío":
  - use `python3 scripts/mailctl.py send-status --draft-id <draft_id>`

## Guardrails

- Sending mail requires explicit user intent.
- Prefer `draft_id` over any inferred lead-level behavior.
- If `send-draft` fails, report the backend error plainly.
- Copy `status`, `provider`, `provider_message_id`, `recipient_email`, `sent_at`, and `error` exactly from wrapper JSON.
- Do not claim a message was sent unless `mailctl` returns a delivery record with `status: sent`.
