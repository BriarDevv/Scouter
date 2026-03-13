---
name: clawscout-leader
description: "Use ClawScout's local API through scripts/clawscoutctl.py for live operational queries and safe control actions. Use this when the user asks for system overview, top leads, recent drafts, recent pipelines, task health, recent activity, or active LLM settings, and when they explicitly want safe actions like generating a draft, running a pipeline, or checking task status."
metadata: { "openclaw": { "emoji": "🦀", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Leader Skill

ClawScout remains the source of truth. Always prefer the local API wrapper over reading database state or guessing from files.

## Use this skill for

- System overview and operator status
- Top-scoring leads
- Recent drafts, pipelines, tasks, and activity
- Active LLM settings by role
- Safe actions explicitly requested by the user:
  - generate a draft for a lead
  - run the full pipeline for a lead
  - check task status

## Do not use this skill for

- Reviewer-by-default decisions
- Direct database inspection when the API already exposes the state
- Destructive actions
- Mail, WhatsApp, or browser-channel automation

## Reviewer rule

- `reviewer` is a deep second opinion under demand.
- The normal ClawScout pipeline still uses `executor`.
- Do not claim reviewer ran unless a separate reviewer flow exists and was invoked explicitly.

## Commands

Run commands from the ClawScout workspace root:

```bash
python3 scripts/clawscoutctl.py overview
python3 scripts/clawscoutctl.py top-leads --limit 10
python3 scripts/clawscoutctl.py recent-drafts --limit 10
python3 scripts/clawscoutctl.py recent-pipelines --limit 10
python3 scripts/clawscoutctl.py task-health --limit 10
python3 scripts/clawscoutctl.py activity --limit 10
python3 scripts/clawscoutctl.py settings-llm
python3 scripts/clawscoutctl.py generate-draft --lead-id <lead_id>
python3 scripts/clawscoutctl.py run-pipeline --lead-id <lead_id>
python3 scripts/clawscoutctl.py task-status --task-id <task_id>
```

## Usage rules

- Read-only commands are preferred for normal operational questions.
- Mutating commands must only be used when the user asked for that action clearly.
- The wrapper returns stable JSON with:
  - `ok`
  - `command`
  - `request`
  - `status_code`
  - `data` or `error`
- When answering, ground the response in that JSON and mention failures plainly.
