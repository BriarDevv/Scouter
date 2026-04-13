# repo-architecture-audit SKILL

autopilot: Act as a Principal Engineer + Repo Architect + DX Auditor + AI Navigation Specialist.

Goal:
Audit the repository structure file-by-file and folder-by-folder to determine:
- architecture quality
- adherence to best practices
- clarity and scalability
- developer experience
- how comfortable Claude (or any AI) can navigate and reason about the repo

---

## Core Principle

This is NOT a superficial structure review.

You MUST:
- traverse every relevant folder
- understand intent behind structure
- detect inconsistencies and drift
- evaluate real-world maintainability

---

## Execution Strategy (MANDATORY)

1. Enumerate FULL repo tree
2. Group by:
   - backend
   - frontend
   - workers
   - data layer
   - infra/scripts
   - docs
   - skills/agents

3. Traverse folder-by-folder:
   - identify purpose
   - validate naming
   - validate boundaries
   - detect redundancy
   - detect misplaced files

4. Traverse file-by-file (where relevant):
   - detect structural smells
   - detect bad co-location
   - detect hidden coupling

5. Explicitly state:
   - what was analyzed
   - what was skipped (and why)

---

## Folder-Level Audit Rules

For EACH folder:

Evaluate:
- clarity of purpose
- naming quality
- cohesion
- coupling with other folders
- scalability

Ask:
- Does this folder belong here?
- Should it be split?
- Should it be merged?
- Is it discoverable?

---

## File Placement Audit

Detect:
- misplaced files
- duplicated responsibility across files
- mixed concerns in same file
- "god folders"
- "misc" / dumping folders

---

## Architectural Best Practices Checklist

Validate:

- clear separation of concerns
- predictable structure
- consistent naming conventions
- domain-driven grouping (if applicable)
- no leaking abstractions
- no circular dependencies (logical)
- infra separated from business logic
- UI not tightly coupled to backend assumptions

---

## AI Navigation Score (VERY IMPORTANT)

Evaluate how easy it is for an AI to understand the repo.

Score based on:
- naming clarity
- discoverability
- consistency
- docs alignment
- signal-to-noise ratio
- absence of misleading abstractions

Output:

AI Navigation Score (1-10):
Explain:
- what helps AI
- what confuses AI
- where it would hallucinate or misinterpret

---

## Human DX Score

Evaluate:
- onboarding ease
- mental overhead
- predictability
- debugging friendliness

---

## Smell Detection

Identify:

- over-nesting
- under-structuring
- flat chaos
- excessive indirection
- duplicated folder structures
- dead folders
- legacy leftovers
- misleading names

---

## Structural Consistency Audit

Detect:

- naming inconsistencies
- pattern drift between modules
- different conventions in different areas
- inconsistent file organization strategies

---

## Kill List (Structure Edition)

List:
- folders to delete
- folders to merge
- folders to split
- folders to rename

Be ruthless.

---

## Ideal Structure Proposal

Propose:
- improved folder structure
- renaming suggestions
- boundary fixes

Keep it realistic (no over-engineering).

---

## Scoring

Score (1-10):

- overall structure
- backend structure
- frontend structure
- folder consistency
- naming quality
- scalability
- maintainability
- AI navigation
- human DX

Explain each score with evidence.

---

## Output Files

Generate:

docs/audits/repo-architecture-deep-audit.md
docs/roadmaps/repo-architecture-refactor-plan.md

---

## Strict Rules

- No generic praise
- No vague criticism
- Every claim must be justified
- Prefer brutal honesty
- Distinguish:
  - confirmed issues
  - suspected issues
  - unknowns

---

## Final Question (MANDATORY)

Answer clearly:

"Is this a 10/10 repo architecture?"

If not:
- why not
- what blocks it from being a 10
