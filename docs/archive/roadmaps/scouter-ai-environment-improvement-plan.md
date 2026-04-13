> **ARCHIVED:** This document has been superseded. See [plans/refactor-roadmap.md](../../plans/refactor-roadmap.md) for the current version.

# Scouter AI Environment Improvement Plan

**Date:** 2026-04-04
**Source:** [scouter-ai-environment-audit.md](../audits/scouter-ai-environment-audit.md)
**Goal:** Take the repo from 7.5/10 to 9/10 AI comfort

---

## Phase 0 — Reduce Friction (30 min)

Quick wins that remove noise without structural changes.

| Task | Effort | Impact |
|------|--------|--------|
| Delete `.codex` (orphan 0-byte file) | 1 min | Remove root noise |
| Delete `HEARTBEAT.md` or move to .claude/ | 1 min | Remove root noise |
| Add `.omx/` to `.gitignore` | 1 min | Hide mystery dir |
| Archive `docs/audits/restructuring-report-2026-04-03.md` to `docs/archive/reports/` | 2 min | Fix unlisted doc |
| Rename archive duplicates: `docs/archive/agent-os-design/{hierarchy,protocols,skills-registry}.md` -> `v0-*.md` | 5 min | Prevent search confusion |

**Definition of Done:** Root has 2 fewer noise files, .gitignore covers .omx/, no duplicate .md names across canonical and archive.

---

## Phase 1 — Clarify Canonical Entry Points (1 hour)

Fix broken references and improve AI onboarding speed.

| Task | Effort | Impact |
|------|--------|--------|
| Create `dashboard/README.md` (frontend quickstart: structure, key files, run, test) | 30 min | Fix broken AGENTS.md reference, guide frontend agents |
| Add 30-second quickstart to top of AGENTS.md | 10 min | Help lightweight/external AIs orient faster |
| Add skills/ to AGENTS.md task routing table | 5 min | Make skills discoverable from entrypoint |
| Create GEMINI.md + CODEX.md shims (same pattern as CLAUDE.md) | 5 min | Multi-AI onboarding |
| Update docs/README.md to list new audit + improvement plan | 5 min | Keep index current |

**Definition of Done:** AGENTS.md has no broken references, all AI platforms have entry shims, skills are discoverable from entrypoint.

---

## Phase 2 — Restructure Docs for AI Discoverability (2 hours)

Fill documentation gaps that force AIs to read source code.

| Task | Effort | Impact |
|------|--------|--------|
| Create `app/llm/PROMPTS.md` — catalog all prompt IDs, roles, versions, contracts | 45 min | Index the 664-line prompts.py for fast lookup |
| Update `docs/architecture/audit.md` — include Agent OS, Scout, outcomes, weekly | 30 min | Align with current reality |
| Mark `docs/architecture/target.md` with staleness note or update | 15 min | Prevent AI confusion |
| Mark `docs/plans/refactor-roadmap.md` with staleness note | 10 min | Same |
| Update `docs/operations/security-backlog.md` — mark closed items | 15 min | Reduce stale todo noise |

**Definition of Done:** No stale docs without staleness markers, prompt system is indexed, architecture doc reflects Agent OS.

---

## Phase 3 — Improve Agent Ergonomics (1 hour)

Make the multi-agent workspace more navigable.

| Task | Effort | Impact |
|------|--------|--------|
| Add `docs/agents/prompt-catalog.md` linking to app/llm/PROMPTS.md | 15 min | Discoverable from Agent OS docs |
| Consolidate Mote references: add "Mote files" section to identities.md | 10 min | Stop spreading Mote across 4 locations |
| Add scoring docs: `docs/agents/scoring.md` (rules, signals, thresholds) | 30 min | Fill the scoring documentation gap |
| Review skills/SKILL.md files against actual code | 15 min | Ensure skills match runtime |

**Definition of Done:** Every agent's files are documented in one place, scoring is documented, prompt system is indexed.

---

## Phase 4 — Improve Multi-Agent Workspace (1 hour)

Support agents with less context and external AIs.

| Task | Effort | Impact |
|------|--------|--------|
| Slim README.md to ~200 lines: move install guide to `docs/operations/install.md` | 30 min | Reduce AI context loading cost |
| Add `.claude/commands/agent-os.md` — common Agent OS operations | 15 min | Pre-built workflow for agent work |
| Add `docs/agents/troubleshooting.md` — common errors and fixes | 15 min | Reduce agent trial-and-error |

**Definition of Done:** README is under 200 lines, AI context loading is faster, common errors are documented.

---

## Phase 5 — Long-Term Repo Habitability (ongoing)

Not urgent, but important for sustained comfort.

| Task | Frequency | Purpose |
|------|-----------|---------|
| Run doc drift check monthly (compare docs to code) | Monthly | Prevent staleness accumulation |
| Keep docs/README.md index updated on every doc addition | Per-change | Maintain discoverability |
| Review archive/ quarterly — delete truly obsolete docs | Quarterly | Prevent archive bloat |
| Keep AGENTS.md under 100 lines | Ongoing | Protect fast AI onboarding |
| Keep root .md count at 4 or fewer (AGENTS, CLAUDE, README, + 1 shim) | Ongoing | Minimize root noise |

---

## Commit Strategy

Phase 0: single commit `chore(repo): clean root noise and archive duplicates`
Phase 1: 2 commits — `docs(dashboard): add frontend README` + `docs(agents): improve AI entrypoint discoverability`
Phase 2: 2 commits — `docs(prompts): add prompt catalog` + `docs(architecture): update for Agent OS reality`
Phase 3: 1 commit `docs(agents): add prompt catalog reference and scoring docs`
Phase 4: 1 commit `docs(repo): slim README and add agent-os command`

Total: ~6 commits, all docs-only, no code changes.

---

## PR Breakdown

All phases can be a single PR or done incrementally on main (docs-only, low risk).

Recommended: Phase 0+1 as one commit batch (quick wins + entry points), Phase 2+3 as another (documentation gaps), Phase 4 separately (README restructuring is more opinionated).

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Over-documenting | Cap total .md at ~80 files. Prefer updating over creating. |
| Docs drift after improvement | Monthly drift check habit. |
| README slim-down breaks human flow | Keep README self-contained with links to detailed docs. |
| Archive rename breaks external links | Archive is internal only — no external links to worry about. |

---

## Definition of Done by Phase

| Phase | Criteria |
|-------|---------|
| 0 | .codex deleted, HEARTBEAT resolved, .omx gitignored, archive duplicates renamed |
| 1 | dashboard/README.md exists, AGENTS.md has quickstart + skills, GEMINI.md/CODEX.md created |
| 2 | Prompt catalog exists, architecture doc updated, stale docs marked |
| 3 | Scoring documented, Mote files consolidated in identities.md, skills verified |
| 4 | README under 200 lines, agent-os command created |
| 5 | Monthly drift checks running, index maintained |
