---
name: clawscout-actions
description: "Mutating actions in ClawScout. Exec: cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact <cmd>. Commands: generate-draft --lead-id ID --wait | run-pipeline --lead-id ID --wait | review-lead --lead-id ID --wait | review-draft --draft-id ID --wait | review-reply --message-id ID | task-status --task-id ID. Only on explicit user request."
metadata: { "openclaw": { "emoji": "⚡", "os": ["linux"], "requires": { "bins": ["python3"] } } }
---

# ClawScout Actions Skill

Mutating operations that change state in ClawScout. Only execute on explicit user request.

## When to use

- "generá un draft para este lead"
- "corré el pipeline para este lead"
- "pedí review del draft / lead / reply"
- Any request that creates, modifies, or triggers something

## When NOT to use

- Read-only queries → use **clawscout-data** or **clawscout-briefs**
- Sending already-approved drafts → use **clawscout-mail**
- Website inspection → use **clawscout-browser**

## Hard rules

1. Only mutate on explicit user request. Never auto-trigger.
2. For final-outcome questions, prefer `--wait`.
3. Return only wrapper JSON.
4. Reviewer model (qwen3.5:27b) is on-demand only — never auto-invoke.
5. `review-reply` is async by default on this machine.

## Commands

```bash
cd /home/briar/src/ClawScout && .venv/bin/python scripts/clawscoutctl.py --data-only --compact <command> [args]
```

| Request | Command |
|---|---|
| Generate draft for lead | `generate-draft --lead-id <id> --wait` |
| Run scoring pipeline | `run-pipeline --lead-id <id> --wait` |
| Check task status | `task-status --task-id <id>` |
| Wait for task | `wait-task --task-id <id>` |
| Review a lead | `review-lead --lead-id <id> --wait` |
| Review a draft | `review-draft --draft-id <id> --wait` |
| Review a reply | `review-reply --message-id <id>` |
| Review a reply (wait) | `review-reply --message-id <id> --wait` |
| Generate reply draft | `reply-response-draft-generate --message-id <id> --wait` |
| Edit reply draft | `reply-response-draft-edit --draft-id <id> --subject "..." --body "..."` |
| Send reply draft | `reply-response-draft-send --draft-id <id>` |
| Review reply draft | `reply-response-draft-review --draft-id <id> --wait` |

## Model routing

| Action type | Model |
|---|---|
| Generate draft | executor (qwen3.5:9b) |
| Run pipeline | executor (qwen3.5:9b) |
| Review lead/draft/reply | reviewer (qwen3.5:27b) |
