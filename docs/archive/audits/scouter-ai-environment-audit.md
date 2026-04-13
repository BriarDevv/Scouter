> **ARCHIVED:** This document has been superseded. See [architecture/audit.md](../../architecture/audit.md) for the current version.

# Scouter AI Environment Audit

**Date:** 2026-04-04
**Auditor perspective:** Staff Engineer + AI Ergonomics Auditor
**Repo:** /home/mateo/Scouter (314 .py, 112 .ts/.tsx, 75 .md, 21 .sh)

---

## 1. Executive Summary

Scouter is an unusually AI-friendly repo for its size (~54K LOC). The onboarding hierarchy (AGENTS.md -> docs/README.md -> task-specific docs) is tighter than 95% of repos this size. Claude Code is genuinely comfortable here. The main friction points are: (a) some dead/orphan files adding noise, (b) docs that drift from code reality, (c) missing dashboard/README.md creating a gap for frontend agents, and (d) archive files with duplicate names that can confuse naive search.

**Overall AI-friendliness: 7.5/10** — above average, with clear paths to 9/10.

---

## 2. First Impression of the Repo

When an AI lands in root and reads the file listing:

**First 30 seconds — what registers:**
- AGENTS.md exists = "there's an AI entrypoint" (strong signal)
- CLAUDE.md exists = "Claude-specific instructions" (strong signal)
- README.md at 494 lines = "comprehensive human docs" (good)
- SOUL.md, IDENTITY.md = "agent personality files" (potentially confusing without context)
- HEARTBEAT.md = "what is this?" (noise)
- .codex = "empty file, why?" (noise)
- 6 .md files in root = moderate clutter for AI attention

**Strong signals:** AGENTS.md + CLAUDE.md provide clear routing. An AI reading CLAUDE.md first gets redirected to AGENTS.md in 3 lines. AGENTS.md then routes by task in a clean table.

**Weak/confusing signals:** SOUL.md and IDENTITY.md look like they might be important onboarding docs but are actually runtime assets for Mote. AGENTS.md line 78 clarifies this, but an AI that reads root files in alphabetical order might waste context on them first.

**Root noise level:** Medium. The root has 18 files + 20 dirs. About 5 of those files (HEARTBEAT.md, .codex, celerybeat-schedule, test.db, scouter.egg-info) add zero value for orientation. Not terrible, but not pristine.

---

## 3. Root Structure Audit

| Item | Assessment |
|------|-----------|
| AGENTS.md (80 lines) | Excellent. Task-based routing table, repo map, editing conventions, validation expectations. |
| CLAUDE.md (12 lines) | Perfect shim. Redirects without duplicating. |
| README.md (494 lines) | Good but long. An AI loading this consumes ~1.5K tokens for content that's mostly human-facing (install guide, Docker setup). |
| SOUL.md (62 lines) | Runtime asset, correctly labeled in AGENTS.md. Could be in app/agent/ to reduce root clutter. |
| IDENTITY.md (10 lines) | Same — runtime asset in root. Small but adds to root file count. |
| HEARTBEAT.md (5 lines) | Near-empty sentinel. No clear consumer. Adds noise. |
| .codex (0 bytes) | Orphan. No references, no purpose. Should be deleted. |
| Makefile (45 lines) | Clean entry point for common operations. |

**Verdict:** Root is functional but could be cleaner. 4 files (SOUL.md, IDENTITY.md, HEARTBEAT.md, .codex) could be relocated or removed.

---

## 4. Discoverability Audit

**How does an AI discover the architecture?**
AGENTS.md:35-47 has a repo map table. This is direct and effective. Score: 9/10.

**How does an AI discover the rules?**
AGENTS.md:49-55 has editing conventions. Clear but brief. The validation expectations at lines 57-61 are excellent. Score: 8/10.

**How does an AI discover canonical vs archive docs?**
docs/README.md has an explicit "Canonical Current Docs" table and "Archive" section. This is well-designed. Score: 9/10.

**How does an AI discover skills?**
skills/ directory is flat with 7 SKILL.md files. MODEL_ROUTING.md provides routing rules. Not referenced from AGENTS.md though — an AI has to know to look in skills/. Score: 6/10.

**How does an AI discover prompts?**
app/llm/prompts.py (664 lines) and app/llm/prompt_registry.py. Not documented in any index. An AI has to grep or know the path. Score: 5/10.

**How does an AI discover the Agent OS docs?**
docs/agents/ has 8 files now (hierarchy, protocols, governance, identities, skills-registry, implementation, whatsapp-strategy, context). Well-organized. Referenced from docs/README.md. Score: 8/10.

**Duplicate paths to same info?**
Yes — docs/archive/agent-os-design/ has hierarchy.md, protocols.md, skills-registry.md with IDENTICAL names to docs/agents/. A search for "hierarchy.md" returns two files. The archive versions are outdated. This is a real confusion risk. Score: 4/10.

---

## 5. Documentation Architecture Audit

**Current structure:**
```
docs/
  README.md           -- index (good)
  agents/             -- 8 canonical Agent OS docs (good)
  architecture/       -- 2 docs + empty ADR dir (gap)
  operations/         -- 2 docs (good)
  plans/              -- 1 doc (sparse)
  product/            -- 1 doc (good)
  audits/             -- 1 doc (unlisted in index)
  archive/            -- 15 historical docs (organized)
```

**What works:**
- Clear canonical/archive separation
- docs/README.md as an index with reading order tables
- Agent OS docs are comprehensive and match code

**What doesn't work:**
- docs/audits/ has 1 unlisted file (restructuring report) — neither canonical nor archived
- Empty ADR directory is a structural promise without content
- No docs for the prompt system (prompts.py, prompt_registry.py, contracts.py)
- No docs for the scoring system (scoring/rules.py)
- dashboard/README.md is referenced in AGENTS.md but doesn't exist

---

## 6. MD Files: Canonical vs Redundant vs Decorative

| Category | Files | Assessment |
|----------|-------|-----------|
| **Canonical** | AGENTS.md, CLAUDE.md, docs/agents/*, docs/architecture/audit.md, docs/architecture/target.md, docs/operations/*, docs/plans/refactor-roadmap.md, docs/product/proposal.md, docs/README.md | 20 files — all useful |
| **Runtime assets** | SOUL.md, IDENTITY.md | 2 files — correctly labeled but root placement adds noise |
| **Decorative/sentinel** | HEARTBEAT.md, .codex | 2 files — remove or relocate |
| **Orphaned** | docs/audits/restructuring-report-2026-04-03.md | 1 file — unlisted, should be archived or indexed |
| **Archive** | docs/archive/** | 15 files — correctly separated |
| **Duplicate names** | docs/archive/agent-os-design/hierarchy.md, protocols.md, skills-registry.md | 3 files — same names as canonical. Rename with v0- prefix |

---

## 7. Claude Comfort Audit

**What helps Claude:**
- AGENTS.md is a near-perfect AI entrypoint — task routing, repo map, conventions
- CLAUDE.md shim prevents confusion
- docs/README.md index with canonical/archive separation
- 7 .claude/commands/ cover common workflows
- Consistent naming conventions (no cross-contamination)
- 315 tests provide safety net for changes
- Architecture guardrail tests prevent structural regressions
- skills/MODEL_ROUTING.md prevents model misuse

**What slows Claude:**
- README.md at 494 lines loads into context but is mostly human install instructions
- No dashboard/README.md = gap when doing frontend work
- No prompt system documentation = must read 664-line prompts.py to understand
- Archive duplicate filenames confuse search
- 45 alembic migrations with non-standard naming (g1a2, h2b3 prefixes)

**What generates friction:**
- SOUL.md/IDENTITY.md in root look important but aren't for most tasks
- HEARTBEAT.md is meaningless to Claude
- .omx/ directory is undocumented
- docs/audits/ has unlisted content

**Claude Comfort Score: 8/10**
Claude is genuinely comfortable here. The onboarding path is clear, the codebase is well-organized, tests are solid. The main friction is noise in root and some documentation gaps.

---

## 8. Other AI Comfort Audit

### Mote/Hermes (8b agent with tools)
**Score: 7/10.** SOUL.md and IDENTITY.md are well-written persona files. The 55 tools in tool_registry provide good coverage. Weekly report injection into system context works. Gap: no structured "Mote handbook" — Mote's capabilities are spread across SOUL.md, tool_registry.py, and core.py.

### Executor/Qwen (9b, single-shot)
**Score: 8/10.** Prompts are well-structured in prompts.py with clear system/data separation. Contracts in contracts.py provide validation. prompt_registry.py maps everything. Gap: no prompt catalog doc — executor has to load 664 lines to understand available prompts.

### Reviewer/Qwen (27b, single-shot)
**Score: 8/10.** Same strengths as Executor. Structured corrections output is well-defined. Gap: same prompt catalog gap.

### Lightweight agent with little context
**Score: 5/10.** A lightweight agent would struggle. AGENTS.md helps but is 80 lines of loading. The task routing table assumes knowledge of the problem domain. No "30-second quickstart" exists. Skills files help but aren't referenced from AGENTS.md.

### External AI (Codex/Gemini/OpenCode) entering cold
**Score: 6/10.** AGENTS.md is the right entry point but requires the AI to understand the reading order convention. README.md would be loaded first by most tools (it's the default), and at 494 lines it's heavy. No GEMINI.md or CODEX.md shims exist (only CLAUDE.md). The overall structure is clear enough that a competent AI would figure it out, but the first 2 minutes would be slower than necessary.

---

## 9. Agent Ergonomics Audit

**Does each agent have "its place"?**
- Mote: app/agent/ + SOUL.md + IDENTITY.md + skills/ (spread across 4 locations)
- Scout: app/agent/research_agent.py + scout_tools.py + scout_prompts.py (concentrated, good)
- Executor: app/llm/ (concentrated, good)
- Reviewer: app/llm/ + app/services/review_service.py (two locations, acceptable)

**Are skills well-located?**
Yes — skills/ is flat and consistent. Each skill has a single SKILL.md. MODEL_ROUTING.md prevents misuse.

**Are prompts well-organized?**
Partially. All in app/llm/prompts.py (664 lines) + app/llm/prompt_registry.py. This is a single large file that grows with every new prompt. Would benefit from a catalog doc, not necessarily splitting the file.

**Does the repo support an AI office?**
Yes — docs/agents/ has hierarchy, protocols, governance, identities, skills-registry. The dashboard has /ai-office. This is well-developed.

---

## 10. Runtime Truth vs Documentation Truth

| Area | Docs Match Code? | Notes |
|------|------------------|-------|
| Agent hierarchy | Yes | docs/agents/hierarchy.md matches app/agent/ and app/llm/ |
| Protocols | Yes | docs/agents/protocols.md matches context_service.py and pipeline flow |
| WhatsApp strategy | Partially | Template names in docs but not yet created in Kapso panel |
| Implementation report | Yes | Updated 2026-04-04 with current backlog |
| Architecture audit | Stale | docs/architecture/audit.md predates Agent OS — doesn't mention Scout, outcomes, weekly |
| Target architecture | Stale | docs/architecture/target.md is from pre-Agent OS planning |
| Refactor roadmap | Stale | docs/plans/refactor-roadmap.md predates Agent OS completion |
| Security backlog | Partially stale | Some items closed but not marked |

**Claude trust level:** Can trust Agent OS docs (agents/) completely. Should verify architecture/ and plans/ against code. Archive is historical only.

---

## 11. Context Loading Cost

**Fast context areas (< 100 lines to understand):**
- AGENTS.md (80 lines) — excellent
- docs/agents/hierarchy.md (66 lines) — excellent
- skills/MODEL_ROUTING.md (30 lines) — excellent
- CLAUDE.md (12 lines) — excellent

**Medium context areas (100-500 lines):**
- docs/agents/protocols.md (~100 lines) — good
- docs/agents/governance.md (~80 lines) — good
- README.md (494 lines) — heavy for AI, mostly human install guide

**Heavy context areas (500+ lines):**
- app/llm/prompts.py (664 lines) — no index, must read or grep
- app/services/setup_service.py (390+ lines) — complex readiness logic
- dashboard/types/index.ts (~800 lines) — large type definition file

**Duplicated context:**
- Minimal. CLAUDE.md correctly defers to AGENTS.md rather than duplicating.
- Only real duplication: archive files with same names as canonical docs.

---

## 12. Naming / Navigation Audit

**Naming: 10/10.** Zero inconsistencies. Backend=snake_case, frontend=kebab-case, docs=kebab-case.

**Navigation: 7/10.** Good but with gaps:
- An AI looking for "how scoring works" would check app/scoring/ (correct) but there's no scoring doc
- An AI looking for "prompt templates" would need to know app/llm/prompts.py specifically
- An AI looking for "dashboard setup" would follow AGENTS.md to dashboard/README.md which doesn't exist

---

## 13. What Feels Great

1. AGENTS.md task routing table — best-in-class AI onboarding
2. CLAUDE.md shim pattern — clean, no duplication
3. docs/README.md canonical/archive separation — clear hierarchy
4. docs/agents/ comprehensive suite — hierarchy, protocols, governance, identities, skills
5. .claude/commands/ — 7 workflows pre-built
6. Architecture guardrail tests — structural regression prevention
7. skills/MODEL_ROUTING.md anti-patterns — prevents model misuse
8. Consistent naming conventions — zero cross-contamination

---

## 14. What Feels Frictional

1. Root clutter — 6 .md files + .codex + HEARTBEAT.md compete for attention
2. Missing dashboard/README.md — broken reference, frontend gap
3. Archive duplicate names — hierarchy.md exists in two places
4. No prompt catalog doc — 664-line file with no index
5. Stale architecture docs — audit.md and target.md predate Agent OS
6. README.md too long — 494 lines mostly for humans, loads into AI context
7. .omx/ undocumented — mystery directory
8. docs/audits/ unlisted file — neither canonical nor archived

---

## 15. What Would Make Claude Much More Comfortable

1. **Create dashboard/README.md** — fixes broken reference, guides frontend work
2. **Delete .codex and HEARTBEAT.md** — reduce root noise
3. **Add .omx/ to .gitignore** — stop mystery dir from appearing
4. **Rename archive duplicates** — v0-hierarchy.md, v0-protocols.md, v0-skills-registry.md
5. **Create app/llm/PROMPTS.md** — catalog of all prompt IDs, roles, and versions
6. **Update docs/architecture/audit.md** — include Agent OS, or mark as stale
7. **Move SOUL.md and IDENTITY.md** to app/agent/ with root symlinks for tooling
8. **Add skills/ reference to AGENTS.md** — currently undiscoverable from AI entrypoint

---

## 16. What Would Make Other AIs More Comfortable

1. **Add GEMINI.md and CODEX.md shims** — same pattern as CLAUDE.md, redirect to AGENTS.md
2. **Create a 30-second quickstart** in AGENTS.md header — "Scouter is X. Start at AGENTS.md. Run tests with Y."
3. **Shrink README.md AI footprint** — move install guide to docs/operations/install.md, keep README under 200 lines
4. **Document the scoring system** — app/scoring/ has no docs

---

## 17. Scorecard

### By Area (1-10)

| Area | Score | Rationale |
|------|-------|-----------|
| Claridad estructural | 8 | Clean package boundaries, consistent naming. Root slightly cluttered. |
| Discoverability | 7 | AGENTS.md is great. Skills and prompts undiscoverable from entrypoint. |
| Agent ergonomics | 7 | Good hierarchy docs. Mote assets spread across 4 locations. |
| Documentation architecture | 7 | Canonical/archive clear. Some stale docs, missing prompt/scoring/dashboard docs. |
| Claude comfort | 8 | Near-excellent. Minor friction from root noise and missing dashboard docs. |
| Multi-agent comfort | 7 | Agent OS docs are solid. Lightweight agents would struggle. |
| Context efficiency | 7 | Fast core paths. README too heavy. No prompt index. |
| Maintainability for autonomous work | 8 | Tests, guardrails, conventions all support safe evolution. |
| **Overall** | **7.5** | |

### By Actor (1-10)

| Actor | Score | Rationale |
|-------|-------|-----------|
| Claude Code | 8 | Clear entrypoint, good commands, solid test safety net |
| Mote/Hermes | 7 | Good persona files, tools, but capabilities are spread |
| Executor | 8 | Clean prompt/contract system, just needs a catalog |
| Reviewer | 8 | Same as Executor |
| Lightweight AI | 5 | No 30-second quickstart, AGENTS.md assumes domain knowledge |
| External AI (cold entry) | 6 | README is heavy, no GEMINI.md/CODEX.md shims |

---

## 18. Top 10 Improvements

| # | Change | Effort | Impact |
|---|--------|--------|--------|
| 1 | Create dashboard/README.md | Low | Fixes broken ref, guides frontend agents |
| 2 | Delete .codex + HEARTBEAT.md | Trivial | Reduce root noise |
| 3 | Add skills/ reference to AGENTS.md | Trivial | Make skills discoverable |
| 4 | Rename archive duplicate .md files | Low | Prevent search confusion |
| 5 | Create app/llm/PROMPTS.md catalog | Medium | Index all prompts for AI and humans |
| 6 | Add .omx/ to .gitignore | Trivial | Remove mystery dir |
| 7 | Update stale architecture docs | Medium | Align docs with Agent OS reality |
| 8 | Move README install guide to docs/ | Medium | Shrink README for AI context efficiency |
| 9 | Add 30-second quickstart to AGENTS.md | Low | Help lightweight/external AIs |
| 10 | Create GEMINI.md + CODEX.md shims | Trivial | Multi-AI onboarding |

---

## 19. Quick Wins

- Delete .codex (1 second)
- Add `.omx/` to .gitignore (1 line)
- Add skills/ mention to AGENTS.md task table (2 lines)
- Rename 3 archive files with v0- prefix (3 renames)
- Archive docs/audits/restructuring-report into docs/archive/reports/

---

## 20. What Not to Touch

- **AGENTS.md structure** — it works, don't reorganize it
- **docs/agents/** — just updated, comprehensive, matches code
- **.claude/commands/** — functional, covers the right workflows
- **skills/ directory layout** — flat is correct, don't nest
- **Backend/frontend naming** — perfect, don't mix conventions
- **Archive docs** — leave them as historical context
- **test_arch_guardrails.py** — this is a gem, protect it

---

## 21. Recommended Target Structure

No major restructuring needed. The repo is well-organized. Target changes:

```
Root (slim down):
  - Remove: .codex, HEARTBEAT.md
  - Keep: AGENTS.md, CLAUDE.md, README.md (shorter), Makefile, etc.
  - SOUL.md + IDENTITY.md: keep in root (tooling compatibility)

docs/ (fill gaps):
  - Add: agents/prompt-catalog.md (from app/llm/ content)
  - Update: architecture/audit.md (include Agent OS)
  - Archive: docs/audits/restructuring-report -> archive/reports/
  - Rename: archive/agent-os-design/hierarchy.md -> v0-hierarchy.md (etc)

dashboard/ (fix gap):
  - Add: dashboard/README.md

AGENTS.md (add skills):
  - Add skills/ to task routing table
  - Add 30-second quickstart header
```

---

## 22. Risks / Anti-Patterns

| Risk | Severity | Notes |
|------|----------|-------|
| Over-documenting | Medium | 75 .md files is approaching the point where docs become a maintenance burden. Be selective. |
| Docs drift from code | Medium | architecture/audit.md and target.md already stale. New docs will drift too if not maintained. |
| Archive confusion | Low | Duplicate names are a minor risk. Renaming fixes it. |
| Root creep | Low | Every tool wants a root config file. Resist adding more .md files to root. |

---

## 23. Final Verdict

Scouter is a **genuinely good AI habitat**. The AGENTS.md -> docs/README.md onboarding hierarchy is best-in-class. The Agent OS documentation suite is comprehensive and matches the code. The test safety net (315 tests + arch guardrails) supports confident autonomous work.

The repo needs polish, not renovation. The top improvements are all low-to-medium effort with high returns: fix the broken dashboard/README.md reference, clean root noise, make skills discoverable, and create a prompt catalog.

**If the top 5 quick wins are applied, this repo goes from 7.5/10 to 8.5/10 for AI comfort.** That's an excellent score for a ~54K LOC production system.
