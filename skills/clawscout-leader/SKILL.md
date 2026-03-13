---
name: clawscout-leader
description: "Use ClawScout wrappers for exact operational data, grounded reply summaries, safe async workflows, and reviewer-on-demand checks."
metadata: { "openclaw": { "emoji": "🦀", "always": true, "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Leader Skill

ClawScout is the source of truth. For exact operational data, execute the local wrapper first and return its JSON exactly.

## Hard rule for grounded queries

For exact counts, IDs, statuses, model names, lead lists, draft lists, task lists, and reply lists:

1. Do not answer from memory.
2. Do not describe a plan.
3. Do not mention capabilities, limits, or missing context.
4. Do not inspect repo files or call raw endpoints if a wrapper command exists.
5. Execute exactly one `exec` tool call first.
6. The final answer must be the wrapper JSON only.
7. Do not wrap JSON in Markdown fences.
8. Do not prepend commentary like "voy a consultar", "voy a usar", or "NO_REPLY".

Never read `AGENTS.md`, `HEARTBEAT.md`, `SOUL.md`, `TOOLS.md`, or other workspace files for these exact-data queries.
Never use `session_status` for ClawScout business data.

If the wrapper returns an error, return only the error JSON.

## Exact-data commands

Run commands from the workspace root with the repo venv:

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact ops-replies-summary --hours <n>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact ops-important-replies --limit <n> --hours <n>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact ops-settings-llm
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact ops-top-leads --limit <n>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact ops-recent-drafts --limit <n>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact ops-overview
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact recent-pipelines --limit <n>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact task-health --limit <n>
```

Map grounded requests as follows:

- reply summary or inbox counts -> `ops-replies-summary`
- important replies or priorities -> `ops-important-replies`
- active models / role models -> `ops-settings-llm`
- top / best leads -> `ops-top-leads`
- recent drafts -> `ops-recent-drafts`
- overview numbers -> `ops-overview`
- recent pipelines -> `recent-pipelines`
- running / failed tasks -> `task-health`

Never derive counts from filtered lists.

## Action workflows

Only mutate state on explicit user request.

Use these commands:

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact generate-draft --lead-id <lead_id> --wait
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact run-pipeline --lead-id <lead_id> --wait
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact task-status --task-id <task_id>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact wait-task --task-id <task_id>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact review-lead --lead-id <lead_id> --wait
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact review-draft --draft-id <draft_id> --wait
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact review-reply --message-id <message_id>
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact review-reply --message-id <message_id> --wait
```

Rules:

- For final-outcome questions, prefer `--wait`.
- Return only the wrapper JSON.
- `reviewer` is on-demand only.
- `review-reply` is async by default on this machine.

## Browser and mail

For public website inspection, use `scripts/browserctl.py`.

For draft send/status, use `scripts/mailctl.py`.

Do not use built-in browser tooling or direct SMTP access when the wrapper already covers the request.
