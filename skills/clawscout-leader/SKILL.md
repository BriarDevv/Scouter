---
name: clawscout-leader
description: "Use ClawScout's local API through scripts/clawscoutctl.py for live operational queries, safe async workflows, and reviewer-on-demand checks. Use this when the user asks for system overview, best leads, recent drafts, recent pipelines, task health, activity, active LLM settings, or explicit actions like generating drafts, running pipelines, checking task status, or requesting reviewer second opinions."
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
  - check task status or wait for completion
  - ask reviewer for a second opinion on a lead or draft

## Do not use this skill for

- Reviewer-by-default decisions
- Direct database inspection when the API already exposes the state
- Destructive actions
- Mail, WhatsApp, or browser-channel automation

## Reviewer rule

- `reviewer` is a deep second opinion under demand.
- The normal ClawScout pipeline still uses `executor`.
- Do not claim reviewer ran unless a dedicated reviewer command was invoked explicitly.
- Never run reviewer automatically when the user only asked for the normal pipeline, normal drafts, or normal status checks.

## Command map

Run commands from the ClawScout workspace root:

```bash
python3 scripts/clawscoutctl.py overview
python3 scripts/clawscoutctl.py best-leads --limit 10
python3 scripts/clawscoutctl.py recent-drafts --limit 10
python3 scripts/clawscoutctl.py drafts-ready --limit 10
python3 scripts/clawscoutctl.py recent-pipelines --limit 10
python3 scripts/clawscoutctl.py task-health --limit 10
python3 scripts/clawscoutctl.py running-tasks --limit 10
python3 scripts/clawscoutctl.py failed-tasks --limit 10
python3 scripts/clawscoutctl.py activity --limit 10
python3 scripts/clawscoutctl.py performance-summary --limit 3
python3 scripts/clawscoutctl.py settings-llm
python3 scripts/clawscoutctl.py generate-draft --lead-id <lead_id> --wait
python3 scripts/clawscoutctl.py run-pipeline --lead-id <lead_id> --wait
python3 scripts/clawscoutctl.py task-status --task-id <task_id>
python3 scripts/clawscoutctl.py wait-task --task-id <task_id>
python3 scripts/clawscoutctl.py review-lead --lead-id <lead_id> --wait
python3 scripts/clawscoutctl.py review-draft --draft-id <draft_id> --wait
```

Prefer one wrapper command per question unless the user explicitly asks for a multi-part answer.

- Overview and system snapshot questions:
  - run only `python3 scripts/clawscoutctl.py overview`
- Top leads:
  - run `python3 scripts/clawscoutctl.py best-leads --limit <n>`
- Recent drafts:
  - run only `python3 scripts/clawscoutctl.py recent-drafts --limit <n>`
- Drafts ready to review/send:
  - run `python3 scripts/clawscoutctl.py drafts-ready --limit <n>`
- Recent pipelines:
  - run only `python3 scripts/clawscoutctl.py recent-pipelines --limit <n>`
- Task health / failures / running work:
  - run `python3 scripts/clawscoutctl.py task-health --limit <n>`
  - if the user asks specifically for running work, prefer `python3 scripts/clawscoutctl.py running-tasks --limit <n>`
  - if the user asks specifically for failures, prefer `python3 scripts/clawscoutctl.py failed-tasks --limit <n>`
- Activity:
  - run only `python3 scripts/clawscoutctl.py activity --limit <n>`
- Performance summary:
  - run `python3 scripts/clawscoutctl.py performance-summary --limit <n>`
- Active models and LLM settings:
  - run only `python3 scripts/clawscoutctl.py settings-llm`
- Generate a draft for a lead:
  - run `python3 scripts/clawscoutctl.py generate-draft --lead-id <lead_id> --wait`
  - use the returned summary as the answer when the user wants the final outcome
- Run the full pipeline for a lead:
  - run `python3 scripts/clawscoutctl.py run-pipeline --lead-id <lead_id> --wait`
  - use the returned summary as the answer when the user wants the final outcome
- Check the status of a task:
  - run `python3 scripts/clawscoutctl.py task-status --task-id <task_id>`
  - if the user asks to wait until it finishes, run `python3 scripts/clawscoutctl.py wait-task --task-id <task_id>`
- Reviewer second opinion on a lead:
  - run `python3 scripts/clawscoutctl.py review-lead --lead-id <lead_id> --wait`
- Reviewer second opinion on a draft:
  - run `python3 scripts/clawscoutctl.py review-draft --draft-id <draft_id> --wait`

## Workflow rules

- For "dame los mejores leads":
  - use `best-leads`
- For "mostrame drafts listos":
  - use `drafts-ready`
- For "qué falló hoy":
  - start with `failed-tasks`
- For "qué está corriendo ahora":
  - use `running-tasks`
- For "qué pipelines salieron bien o mal":
  - use `recent-pipelines`
- For "qué está rindiendo mejor":
  - use `performance-summary`
- For "qué modelo usa cada rol":
  - use `settings-llm`
- For `generate-draft` and `run-pipeline`:
  - prefer the `--wait` workflow unless the user explicitly wants just the task id
  - when `--wait` succeeds, answer with the wrapper `summary` fields rather than free-form narration
- For reviewer:
  - only use `review-lead --wait` or `review-draft --wait` when the user explicitly asks for deeper review, second opinion, or reviewer
  - always mention that reviewer used the premium second-opinion path and report the returned `role` and `model`

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
- For `generate-draft --wait`, `run-pipeline --wait`, `review-lead`, and `review-draft`, prefer returning the `summary` or review payload fields directly instead of paraphrasing them loosely.
- For `generate-draft --wait`, `run-pipeline --wait`, `review-lead --wait`, and `review-draft --wait`, prefer returning the `summary` or review payload fields directly instead of paraphrasing them loosely.

## Mutation rules

- Read-only commands are preferred unless the user clearly requested an action.
- Mutating commands in this skill are limited to:
  - `generate-draft`
  - `run-pipeline`
  - `task-status` and `wait-task` follow-up checks after an action
  - `review-lead`
  - `review-draft`
- Do not change lead status from this skill.
- Do not trigger reviewer automatically.
