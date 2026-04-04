# Scouter Documentation Map

This directory separates canonical current documentation from historical material.

If you are an AI coding assistant, start with [../AGENTS.md](../AGENTS.md).
If you are a human operator or developer, start with [../README.md](../README.md).

## Canonical Current Docs

| Area | Document | Purpose |
| --- | --- | --- |
| Architecture | [architecture/audit.md](architecture/audit.md) | Current-state architecture assessment |
| Architecture | [architecture/target.md](architecture/target.md) | Target architecture direction |
| Plans | [plans/refactor-roadmap.md](plans/refactor-roadmap.md) | Active refactor roadmap |
| Agent OS | [agents/agent-os-implementation.md](agents/agent-os-implementation.md) | Agent OS implementation reference (what was built) |
| Agent OS | [agents/hierarchy.md](agents/hierarchy.md) | Team structure, who decides what |
| Agent OS | [agents/protocols.md](agents/protocols.md) | Communication, feedback loops, error handling |
| Agent OS | [agents/governance.md](agents/governance.md) | Runtime modes, approvals, security, LOW_RESOURCE_MODE |
| Agent OS | [agents/identities.md](agents/identities.md) | Agent identity cards (Mote, Scout, Executor, Reviewer) |
| Agent OS | [agents/skills-registry.md](agents/skills-registry.md) | All agent/model skills with implementation paths |
| Agent OS | [agents/scoring.md](agents/scoring.md) | Lead scoring rules, weights, thresholds |
| Agent OS | [agents/whatsapp-outreach-strategy.md](agents/whatsapp-outreach-strategy.md) | WhatsApp template strategy + Closer flow |
| Agent OS | [agents/context.md](agents/context.md) | Operator and agent runtime context |
| Operations | [operations/local-dev-wsl.md](operations/local-dev-wsl.md) | Local WSL and runtime workflow |
| Operations | [operations/security-backlog.md](operations/security-backlog.md) | Deferred security backlog |
| Product | [product/proposal.md](product/proposal.md) | Product and positioning context |
| Audits | [audits/scouter-ai-environment-audit.md](audits/scouter-ai-environment-audit.md) | AI environment audit and scorecard |
| Roadmaps | [roadmaps/scouter-ai-environment-improvement-plan.md](roadmaps/scouter-ai-environment-improvement-plan.md) | AI environment improvement plan |

## Start Here By Goal

| Goal | Read in this order |
| --- | --- |
| Understand the Agent OS | [agents/hierarchy.md](agents/hierarchy.md) -> [agents/protocols.md](agents/protocols.md) -> [agents/identities.md](agents/identities.md) |
| Set up WhatsApp outreach | [agents/whatsapp-outreach-strategy.md](agents/whatsapp-outreach-strategy.md) |
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
- `archive/agent-os-design/` for pre-implementation Agent OS design docs (audit, plan, hierarchy, protocols, skills-registry)
- `archive/superpowers/` for older design and planning artifacts

Archive docs are useful for context, but they are not the canonical source of truth.
