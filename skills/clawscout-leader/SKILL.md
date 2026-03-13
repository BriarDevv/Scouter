---
name: clawscout-leader
description: "Use ClawScout's local API through scripts/clawscoutctl.py for live operational queries and safe control actions. Use this when the user asks for system overview, top leads, recent drafts, recent pipelines, task health, recent activity, or active LLM settings, and when they explicitly want safe actions like generating a draft, running a pipeline, or checking task status."
metadata: { "openclaw": { "emoji": "🦀", "always": true, "os": ["linux"], "requires": { "bins": ["python3"] } } }
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

## Command map

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

Use exactly one wrapper command per question type unless the user explicitly asks for a multi-part answer.

- Overview and system snapshot questions:
  - run only `python3 scripts/clawscoutctl.py overview`
- Top leads:
  - run only `python3 scripts/clawscoutctl.py top-leads --limit <n>`
- Recent drafts:
  - run only `python3 scripts/clawscoutctl.py recent-drafts --limit <n>`
- Recent pipelines:
  - run only `python3 scripts/clawscoutctl.py recent-pipelines --limit <n>`
- Task health / failures / running work:
  - run only `python3 scripts/clawscoutctl.py task-health --limit <n>`
- Activity:
  - run only `python3 scripts/clawscoutctl.py activity --limit <n>`
- Active models and LLM settings:
  - run only `python3 scripts/clawscoutctl.py settings-llm`
- Generate a draft for a lead:
  - run only `python3 scripts/clawscoutctl.py generate-draft --lead-id <lead_id>`
- Run the full pipeline for a lead:
  - run only `python3 scripts/clawscoutctl.py run-pipeline --lead-id <lead_id>`
- Check the status of a task:
  - run only `python3 scripts/clawscoutctl.py task-status --task-id <task_id>`

## Grounding rules

- ClawScout is the source of truth. Do not answer operational questions from memory, repo files, or model intuition when `clawscoutctl` already exposes the data.
- For counts, IDs, statuses, scores, timestamps, and model names, copy values exactly from wrapper JSON.
- For machine-readable answers, prefer compact JSON objects with named keys over bare arrays.
- Never derive a global metric from the length of a list returned by another command.
  - Example: never infer `total_leads` from `top-leads`.
- If the user asks for overview numbers, use `overview` and only `overview`.
- If the user asks for settings/model configuration, use `settings-llm` and only `settings-llm`.
- If the user asks for exact JSON, return only the requested fields copied verbatim from `data`.
- If the requested field is missing from wrapper output, say it is unavailable. Do not estimate or backfill it from another command.
- Mention failures plainly using the wrapper `error` field when a command fails.

## Mutation rules

- Read-only commands are preferred unless the user clearly requested an action.
- Mutating commands in this skill are limited to:
  - `generate-draft`
  - `run-pipeline`
  - `task-status` follow-up checks after an action
- Do not change lead status from this skill.
- Do not trigger reviewer automatically.
