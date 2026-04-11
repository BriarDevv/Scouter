# Scouter Scripts

Two audiences share this directory. Know which one you are before running anything.

## Operator scripts

Human developers running Scouter locally or in CI. These are the scripts the Makefile calls and the ones you should reach for from a shell.

| Script | Called by | Purpose |
|---|---|---|
| `scouter.sh` | `make up`, `make down`, `make restart`, `make status`, `make logs`, `make preflight`, `make seed`, `make nuke` | Master orchestration — starts/stops the full stack (Postgres, Redis, API, Worker, Beat, Dashboard) with kill-safe port logic. Delegates dev lanes to `dev-up.sh` / `dev-down.sh`. |
| `dev-up.sh` | `scouter.sh start`, `make dev-up` | Production-grade daemon launcher: runs migrations, starts uvicorn + `next dev`, records PIDs in `.dev-runtime/`, kills only Scouter-owned listeners on clashing ports. |
| `dev-down.sh` | `scouter.sh stop`, `make dev-down` | Symmetric shutdown using the same port-owner verification. |
| `dev-status.sh` | `scouter.sh status`, `make dev-status` | Health probe: checks backend `/health`, `/api/v1/settings/mail`, `/api/v1/mail/inbound/status`, dashboard `/settings`, `/responses`. |
| `start-local-stack.sh` | Direct developer invocation | **Different** from `dev-up.sh`. Prints a copy-pasteable start guide and optionally launches services into tmux sessions (`scouter-api`, `scouter-worker`, `scouter-dashboard`) with `--launch`. Use when you want interactive dev with per-service tmux panes; use `dev-up.sh` when you want a single daemon start. |
| `init.sh` | First-time setup | Bootstrap: creates venv, installs deps, runs migrations. |
| `preflight.py` | `scouter.sh preflight` | Verifies environment, secrets, service reachability. |
| `seed.py` | `scouter.sh seed` | Loads test data into a local database. |
| `export.sh` / `import.sh` | Manual | Backup and restore Scouter's Postgres + Redis + configs as a portable ZIP. |
| `migrate-legacy-stack.sh` | `scouter.sh start` (automatic) | **Legacy, time-bounded**. Migrates volumes from the pre-rename `clawscout_*` Docker stack to `scouter_*`. This was added when the project was renamed from clawscout and should be archived once no developer has a legacy environment — target TTL **2026-07-01**. The same automatic detection in `scouter.sh` (`legacy_container_present`) should be removed at the same time. |

Operators should **never** need to touch the agent CLIs below.

## Agent CLIs

These are HTTP-API wrappers used by AI agents (Mote, Scout, dashboard skills) to operate Scouter through the public API. They are not general-purpose dev tools. Every command maps to a `COMMAND_SPEC` which declares the HTTP method, path template, and whether it mutates state. The agent reads this contract and calls the CLI from skills under `skills/scouter-*/SKILL.md`.

| Script | Primary audience | Purpose | Skills that use it |
|---|---|---|---|
| `scouterctl.py` | Mote, Scout, dashboard skills | HTTP API wrapper covering ~35 endpoints: `leader/overview`, `outreach/drafts`, `reviews/*`, `notifications/*`, `tasks/*`, `whatsapp/*`, etc. Supports sync, async (`--wait` polls task status), `--data-only`, and `--compact` output modes. | `scouter-actions`, `scouter-data`, `scouter-notifications`, `scouter-whatsapp`, `.claude/commands/agent-os.md` |
| `browserctl.py` | Scout | Playwright-based web inspector: `inspect-url`, `inspect-business-site --lead-id`. Returns grounded JSON (title, meta, h1, CTA signals, social links, phones, emails, screenshots). Has an `ensure_playwright_runtime()` shim that auto re-execs under `.venv/bin/python3` if playwright is missing from the current interpreter. **Path-sensitive**: reads `SCRIPT_PATH.parent.parent` as the workspace root to find `.venv/`. | `scouter-browser` |
| `mailctl.py` | Dashboard skills | Draft management CLI: `recent-drafts`, `draft-detail`, `send-status`, `send-draft`. | `scouter-mail` |

### Audience rules for agent CLIs

- **Do not** delete them. They are first-class agent tools, not AI slop.
- **Do not** move them without updating `skills/*/SKILL.md`, `.claude/commands/agent-os.md`, `docs/audits/*` that reference the exact `scripts/<name>.py` path. `browserctl.py` additionally requires fixing `SCRIPT_PATH.parent.parent` if its nesting changes.
- **Do not** add new operator-facing commands to `scouterctl.py`. If an operator needs a new action, add a Makefile target or a `scouter.sh` subcommand. `scouterctl.py`'s audience is agents.
- When adding a new `COMMAND_SPEC` to `scouterctl.py`, keep it aligned with the corresponding SKILL.md description — the skill prompts read the CLI's command surface literally.

## Directory hygiene

- Operator scripts produce logs in `./logs/` and PIDs in `./.pids/` / `./.dev-runtime/`. Both paths are gitignored.
- `celerybeat-schedule` at the repo root is the Celery beat state file; also gitignored.
- The three agent CLIs have no persistent state — they are stateless HTTP clients with retries and optional polling.

If a script feels like it doesn't fit either audience, it probably needs to split. File an issue before shipping a third category.
