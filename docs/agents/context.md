# Agent and Operator Context

This document is secondary context for humans and AI assistants.
It is not the canonical repo entrypoint. Start with [../../AGENTS.md](../../AGENTS.md)
or [../../README.md](../../README.md) first.

## Operator Context

- Primary operator: Mateo
- Working language: Spanish, rioplatense style
- Environment: WSL2, tmux, local-first workflow
- Preferences:
  - direct communication
  - atomic commits
  - best practices over hacks
  - avoid unnecessary complexity

## Agent Runtime Context

Mote is the operational AI agent for ClawScout.
Its runtime persona lives in [../../SOUL.md](../../SOUL.md) and
[../../IDENTITY.md](../../IDENTITY.md).

Default local model roles:

| Role | Model | Purpose |
| --- | --- | --- |
| LEADER | `qwen3.5:4b` | orchestration, summaries, briefs |
| EXECUTOR | `qwen3.5:9b` | classification, scoring, drafts, dossiers |
| REVIEWER | `qwen3.5:27b` | review and second opinions |
| AGENT | `hermes3:8b` | interactive chat agent |

## External Services

- Google Maps API for territory crawling
- Ollama for local inference
- SMTP / IMAP for outbound and inbound mail
- WhatsApp integrations for approved outreach and alerts
- Telegram integrations for operational notifications

## Celery Queues

| Queue | Typical work |
| --- | --- |
| `default` | crawl and general tasks |
| `enrichment` | website and lead enrichment |
| `scoring` | scoring tasks |
| `llm` | analysis, drafts, briefs |
| `reviewer` | review and second-opinion tasks |
| `research` | lead research workflows |

## When To Use This Doc

Use this file when you need secondary context about:

- who operates the system,
- how the agent is positioned,
- what external services exist,
- or what queue and model assumptions the repo makes.

Do not use it as a substitute for the canonical architecture docs.
