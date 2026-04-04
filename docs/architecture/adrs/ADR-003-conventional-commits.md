# ADR-003: Conventional Commits as the Single Commit Convention

**Status:** Accepted
**Date:** 2026-04-04

## Context

Early git history in the Scouter repository used free-form commit messages: "fix bug", "wip", "update", "changes". This made it impossible to scan history to understand what changed, when, and why. Changelog generation required manual curation. AI coding assistants contributing commits added to the inconsistency by mimicking whatever style was nearby.

The project needed one convention that humans and AI assistants could both follow mechanically.

## Decision

All commits use the Conventional Commits format:

```
type(scope): short imperative description

Optional body explaining why, not what.
```

Valid types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`.

The convention is documented in `AGENTS.md` so that AI assistants (Claude, Codex, Gemini) read and apply it from the same source as human contributors. No additional tooling enforcement (commitlint, husky) is installed at this time; the convention is enforced by code review and AI assistant instruction.

## Consequences

**Positive**
- Git history is scannable: `git log --oneline` communicates intent at a glance.
- Automated changelog generation (`feat` and `fix` commits) is possible without manual curation.
- AI assistants follow the same rules as humans, producing consistent history regardless of who authored the commit.
- Scope tagging (`feat(scoring):`, `fix(outreach):`) localises changes at a glance.

**Negative**
- Requires discipline from every contributor; enforcement is social, not automated.
- Pre-existing commits are non-conforming; the clean history starts from the adoption date, not from the repository's beginning.
- Overly granular scopes require occasional normalisation decisions.

## Alternatives Considered

**GitHub-style PR squash titles only.** Rejected because Scouter does not use a PR-heavy workflow; many commits land directly and need to be self-describing without a PR description to provide context.

**No enforced convention, rely on good judgement.** Rejected because "good judgement" produced the inconsistent history that prompted this decision.

**Commitizen with interactive prompts.** Rejected because it adds tooling friction for AI contributors that operate via CLI and cannot interact with prompts.
