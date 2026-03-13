---
name: clawscout-leader
description: "Use ClawScout's local API through scripts/clawscoutctl.py for live operational queries, reply prioritization, safe async workflows, and reviewer-on-demand checks. Use this when the user asks for system overview, best leads, inbound reply summaries, recent drafts, recent pipelines, task health, activity, active LLM settings, or explicit actions like generating drafts, running pipelines, checking task status, or requesting reviewer second opinions."
metadata: { "openclaw": { "emoji": "🦀", "always": true, "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Leader Skill

ClawScout remains the source of truth. Always prefer the local API wrapper over reading database state or guessing from files.

## Use this skill for

- System overview and operator status
- Inbound reply summary, prioritization, and reviewer candidates
- Top-scoring leads
- Recent drafts, pipelines, tasks, and activity
- Active LLM settings by role
- Public website inspection through `scripts/browserctl.py`
- Controlled mail workflows through `scripts/mailctl.py`
- Safe actions explicitly requested by the user:
  - generate a draft for a lead
  - run the full pipeline for a lead
  - check task status or wait for completion
  - ask reviewer for a second opinion on a lead or draft
  - ask reviewer for a second opinion on an inbound reply

## Do not use this skill for

- Reviewer-by-default decisions
- Direct database inspection when the API already exposes the state
- Destructive actions
- Mail, WhatsApp, or browser-channel automation
- Direct SMTP access when `scripts/mailctl.py` already covers the requested draft send/status workflow
- Built-in browser tooling when `scripts/browserctl.py` already covers the requested public inspection

## Reviewer rule

- `reviewer` is a deep second opinion under demand.
- The normal ClawScout pipeline still uses `executor`.
- Do not claim reviewer ran unless a dedicated reviewer command was invoked explicitly.
- Never run reviewer automatically when the user only asked for the normal pipeline, normal drafts, or normal status checks.

## Command map

Run commands from the ClawScout workspace root:

```bash
python3 scripts/clawscoutctl.py overview
python3 scripts/clawscoutctl.py replies-summary --hours 24
python3 scripts/clawscoutctl.py recent-replies --limit 10 --hours 24
python3 scripts/clawscoutctl.py important-replies --limit 10 --hours 24
python3 scripts/clawscoutctl.py positive-replies --limit 10 --hours 24
python3 scripts/clawscoutctl.py quote-replies --limit 10 --hours 24
python3 scripts/clawscoutctl.py meeting-replies --limit 10 --hours 24
python3 scripts/clawscoutctl.py reviewer-candidates --limit 10 --hours 24
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
python3 scripts/clawscoutctl.py review-reply --message-id <message_id>
python3 scripts/clawscoutctl.py review-reply --message-id <message_id> --wait
python3 scripts/clawscoutctl.py review-reply --message-id <message_id> --sync
python3 scripts/browserctl.py inspect-url --url <public_url>
python3 scripts/browserctl.py inspect-url --url <public_url> --screenshot
python3 scripts/browserctl.py inspect-business-site --lead-id <lead_id>
python3 scripts/browserctl.py inspect-business-site --lead-id <lead_id> --screenshot
python3 scripts/mailctl.py recent-drafts --limit <n>
python3 scripts/mailctl.py draft-detail --draft-id <draft_id>
python3 scripts/mailctl.py send-status --draft-id <draft_id>
python3 scripts/mailctl.py send-draft --draft-id <draft_id>
```

Prefer one wrapper command per question unless the user explicitly asks for a multi-part answer.

- Overview and system snapshot questions:
  - run only `python3 scripts/clawscoutctl.py overview`
- Reply summary and inbox counters:
  - run only `python3 scripts/clawscoutctl.py replies-summary --hours <n>`
- Recent replies:
  - run `python3 scripts/clawscoutctl.py recent-replies --limit <n> --hours <n>`
- Important replies that deserve attention first:
  - run `python3 scripts/clawscoutctl.py important-replies --limit <n> --hours <n>`
- Positive replies:
  - run `python3 scripts/clawscoutctl.py positive-replies --limit <n> --hours <n>`
- Quote requests:
  - run `python3 scripts/clawscoutctl.py quote-replies --limit <n> --hours <n>`
- Meeting requests:
  - run `python3 scripts/clawscoutctl.py meeting-replies --limit <n> --hours <n>`
- Replies that deserve reviewer:
  - run `python3 scripts/clawscoutctl.py reviewer-candidates --limit <n> --hours <n>`
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
- Reviewer second opinion on an inbound reply:
  - by default run `python3 scripts/clawscoutctl.py review-reply --message-id <message_id>` to queue it asynchronously
  - if the user explicitly wants to wait for the reviewer result now, run `python3 scripts/clawscoutctl.py review-reply --message-id <message_id> --wait`
  - only use `python3 scripts/clawscoutctl.py review-reply --message-id <message_id> --sync` as an escape hatch when the user explicitly wants an inline review and accepts that it may be slow on this machine
- Public website inspection by URL:
  - run `python3 scripts/browserctl.py inspect-url --url <public_url>`
  - add `--screenshot` only when the user asked for visual evidence or a screenshot would materially help
- Public website inspection by lead:
  - run `python3 scripts/browserctl.py inspect-business-site --lead-id <lead_id>`
  - add `--screenshot` only when useful
- Drafts ready to send:
  - run `python3 scripts/mailctl.py recent-drafts --limit <n>`
- Draft detail:
  - run `python3 scripts/mailctl.py draft-detail --draft-id <draft_id>`
- Draft send status:
  - run `python3 scripts/mailctl.py send-status --draft-id <draft_id>`
- Send one explicit approved draft:
  - run `python3 scripts/mailctl.py send-draft --draft-id <draft_id>`

## Workflow rules

- For "dame los mejores leads":
  - use `best-leads`
- For "qué replies hubo hoy":
  - use `replies-summary`
- For "qué respuestas positivas tengo":
  - use `positive-replies`
- For "quién pidió presupuesto":
  - use `quote-replies`
- For "quién pidió reunión":
  - use `meeting-replies`
- For "cuáles conviene responder primero":
  - use `important-replies`
- For "cuáles conviene revisar con reviewer":
  - use `reviewer-candidates`
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
- For public website inspection:
  - prefer `python3 scripts/browserctl.py inspect-url --url <public_url>`
  - if the user references a lead id and wants the lead's website, use `python3 scripts/browserctl.py inspect-business-site --lead-id <lead_id>`
  - do not use the built-in OpenClaw browser tool for these grounded inspections unless the user explicitly asks for interactive browsing
- For mail workflows:
  - prefer `python3 scripts/mailctl.py recent-drafts --limit <n>` for send-ready drafts
  - use `draft-detail` before sending if the user asks to inspect content first
  - use `send-draft` only on explicit user request
  - use `send-status` when the user asks what happened with a draft delivery
- For `generate-draft` and `run-pipeline`:
  - prefer the `--wait` workflow unless the user explicitly wants just the task id
  - when `--wait` succeeds, answer with the wrapper `summary` fields rather than free-form narration
- For reviewer:
  - only use `review-lead --wait`, `review-draft --wait`, or `review-reply` when the user explicitly asks for deeper review, second opinion, or reviewer
  - prefer `review-reply` async by default on this machine because reviewer is materially slower than executor
  - always mention that reviewer used the premium second-opinion path and report the returned `role` and `model`

## Grounding rules

- ClawScout is the source of truth. Do not answer operational questions from memory, repo files, or model intuition when `clawscoutctl` already exposes the data.
- For counts, IDs, statuses, scores, timestamps, and model names, copy values exactly from wrapper JSON.
- For reply counts and inbox metrics, use `replies-summary` and only `replies-summary`.
- For machine-readable answers, prefer compact JSON objects with named keys over bare arrays.
- Never derive a global metric from the length of a list returned by another command.
  - Example: never infer `total_leads` from `top-leads`.
- Never infer reply totals from `recent-replies`, `important-replies`, or other filtered reply lists.
- If the user asks for overview numbers, use `overview` and only `overview`.
- If the user asks for reply summary numbers, use `replies-summary` and only `replies-summary`.
- If the user asks for settings/model configuration, use `settings-llm` and only `settings-llm`.
- If the user asks for exact JSON, return only the requested fields copied verbatim from `data`.
- If the requested field is missing from wrapper output, say it is unavailable. Do not estimate or backfill it from another command.
- Mention failures plainly using the wrapper `error` field when a command fails.
- For `generate-draft --wait`, `run-pipeline --wait`, `review-lead --wait`, `review-draft --wait`, and `review-reply`, prefer returning the `summary` or review payload fields directly instead of paraphrasing them loosely.
- For website inspection, copy `title`, `meta_description`, `h1`, `contact_signals`, `social_links`, `cta_signals`, `page_type_guess`, `screenshot_path`, and `important_links` exactly from `browserctl` JSON.
- For mail delivery, copy `status`, `provider`, `provider_message_id`, `recipient_email`, `sent_at`, and `error` exactly from `mailctl` JSON.

## Mutation rules

- Read-only commands are preferred unless the user clearly requested an action.
- Mutating commands in this skill are limited to:
  - `generate-draft`
  - `run-pipeline`
  - `task-status` and `wait-task` follow-up checks after an action
  - `review-lead`
  - `review-draft`
  - `review-reply`
  - `send-draft`
- Do not change lead status from this skill.
- Do not trigger reviewer automatically.
