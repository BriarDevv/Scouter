# ClawScout Documentation Map

This directory separates canonical current documentation from historical material.

If you are an AI coding assistant, start with [../AGENTS.md](../AGENTS.md).
If you are a human operator or developer, start with [../README.md](../README.md).

## Canonical Current Docs

| Area | Document | Purpose |
| --- | --- | --- |
| Architecture | [architecture/audit.md](architecture/audit.md) | Current-state architecture assessment |
| Architecture | [architecture/target.md](architecture/target.md) | Target architecture direction |
| Plans | [plans/refactor-roadmap.md](plans/refactor-roadmap.md) | Active refactor roadmap |
| Operations | [operations/local-dev-wsl.md](operations/local-dev-wsl.md) | Local WSL and runtime workflow |
| Operations | [operations/security-backlog.md](operations/security-backlog.md) | Deferred security backlog |
| Agents | [agents/context.md](agents/context.md) | Secondary operator and agent context |
| Product | [product/proposal.md](product/proposal.md) | Product and positioning context |

## Start Here By Goal

| Goal | Read in this order |
| --- | --- |
| Understand the current architecture | [architecture/audit.md](architecture/audit.md) -> [architecture/target.md](architecture/target.md) |
| Follow the current implementation sequence | [plans/refactor-roadmap.md](plans/refactor-roadmap.md) |
| Run the stack locally | [../README.md](../README.md) -> [operations/local-dev-wsl.md](operations/local-dev-wsl.md) |
| Work effectively with an AI assistant | [../AGENTS.md](../AGENTS.md) -> this file -> task-specific docs |
| Understand product direction | [product/proposal.md](product/proposal.md) |
| Review old decisions or prior execution history | `archive/` |

## Archive

Historical material lives under `archive/`:

- `archive/audits/` for older audit snapshots
- `archive/reports/` for implementation and closure reports
- `archive/roadmaps/` for superseded plans
- `archive/superpowers/` for older design and planning artifacts

Archive docs are useful for context, but they are not the canonical source of truth.

## Legacy Paths

Some old top-level paths remain as short compatibility pointers:

- `docs/architecture-audit.md`
- `docs/target-architecture.md`
- `docs/refactor-roadmap.md`
- `docs/linux-first.md`
- `docs/SECURITY_AUDIT_PENDING.md`
- `docs/clawscout_propuesta.md`

Use the canonical subdirectory paths above for all new references.
