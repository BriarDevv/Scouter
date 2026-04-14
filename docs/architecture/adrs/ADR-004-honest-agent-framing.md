# ADR-004: Honest agent framing — 2 agents + 2 LLM roles

**Status:** Accepted (2026-04-13)

**Context:** The audit in `docs/audits/repo-deep-audit.md` (section 6)
flagged that the project was consistently marketed as "AI Agent OS with
4 roles" while the implementation has only 2 genuine agents (Mote, Scout
— tool-using loops) and 2 stateless LLM invocations (Executor, Reviewer)
that share prompts and models with each other and with Scout.

Calling Executor and Reviewer "agents" created three concrete problems:

1. **Operator expectations drift.** Operators reading the README expected
   emergent multi-agent behaviour (consensus, cross-talk, memory of past
   interactions). The code supports none of that.
2. **Design decisions stall.** Requests like "add an AI meeting" or
   "have the agents vote" didn't have anywhere to land because there are
   no real agents to participate — only prompts to re-run.
3. **Credibility erosion.** Honest internal audits repeatedly caught the
   mismatch. Over time that trust cost exceeds the marketing benefit.

**Decision:** From 2026-04-13 forward, the term **agent** is reserved for
components that:

- Enter a loop with a termination condition (max iterations, timeout,
  or explicit finish call).
- Call tools whose output informs the next step.
- Make branching decisions based on tool output.

Components that issue a single prompted LLM call are **LLM roles**
(stateless invocations specialized by prompt), not agents.

**Consequences:**

- README + `docs/agents/hierarchy.md` both reflect the new framing.
- `AGENTS.md` (the AI coding-assistant entry point) can keep its name —
  that's a filename convention, not a product claim.
- Future docs, ADRs, and marketing use the corrected language.
- Implementation does NOT change. This is purely a naming decision; no
  behaviour is altered.
- The path to adding real multi-agent behaviour (consensus, memory,
  meetings) remains open — but any such feature must be justified
  independently against the criteria in the post-hardening roadmap, not
  claimed as "we already have it".

**Alternatives considered:**

- **Keep the "4 agents" framing, document the disclaimer elsewhere.**
  Rejected — disclaimers buried in docs get lost; the top-level framing
  is the single highest-leverage signal operators see.
- **Rebrand Executor/Reviewer as "mini-agents" so the count stays at 4.**
  Rejected — "mini-agent" dilutes the meaningful distinction between
  looping, tool-using components and stateless prompted calls.

**Follow-up scope:**

- `docs/agents/identities.md` and related files can be updated opportunistically
  when touched for other reasons; no sweeping rewrite is required.
- Commit scopes (`test(agent-os): …`) remain valid — the implementation
  directory is still called `app/agent/` by convention.

**Related docs:**

- `docs/audits/repo-deep-audit.md` (original finding)
- `docs/roadmaps/post-hardening-plan.md` (Item 5 — this ADR closes it)
- `README.md` (updated framing)
- `docs/agents/hierarchy.md` (added Agent vs LLM Role section)
