# repo-deep-audit SKILL

autopilot: Act as a Principal Engineer + Code Auditor + Anti-AI-Slop Reviewer + Reliability Engineer.

Default to a single-agent deep audit.
Escalate to teams ONLY if it materially improves audit quality.

---

## Execution Strategy (MANDATORY)

1. Enumerate repo structure
2. Identify:
   - backend
   - frontend
   - workers
   - data layer
   - tests
   - docs
   - skills
3. Traverse in layers:
   root -> backend -> frontend -> data -> workers -> prompts -> tests -> docs
4. Do NOT skip files unless irrelevant
5. Explicitly mention what was NOT analyzed

---

## Mandatory Phase 0 - Repo Mapping

Before auditing:

- Read README.md
- Read AGENTS.md (if exists)
- Read docs/README.md (if exists)

Build:

- entrypoints
- boundaries (sync/async)
- pipelines
- source-of-truth docs
- hot spots

---

## Evidence Rule (MANDATORY)

Every meaningful finding MUST include:

- file path
- function/module reference
- concrete issue
- why it matters

No vague statements allowed.

---

## Confidence Rule

Each finding must include:

- confidence: HIGH / MEDIUM / LOW

---

## Impact Rule

Each finding must include:

- impact: HIGH / MEDIUM / LOW

---

## Systemic Pattern Detection

Identify repeated issues:

- duplicated logic
- weak error handling
- contract drift
- naming inconsistency
- abstraction misuse

Mark as SYSTEMIC.

---

## AI Slop Qualification Rule

Before marking as slop:

- does it reduce duplication?
- improve clarity?
- isolate complexity?

If NO -> AI SLOP
If YES -> justified

---

## End-to-End Flow Verification

Trace key flows:

- data continuity
- state transitions
- async handoffs
- error propagation

Mark flows as:

- solid
- fragile
- broken
- unverifiable

---

## Kill List

List:

- deletable files
- useless abstractions
- redundant docs

---

## Preserve List

List:

- strong modules
- good patterns
- stable architecture pieces

---

## Output Requirements

Generate:

docs/audits/repo-deep-audit.md
docs/roadmaps/repo-hardening-plan.md

---

## Scoring

Score (1-10):

- structure
- backend
- frontend
- pipelines
- data model
- testing
- docs
- maintainability
- correctness
- AI slop

---

## Strict Rules

- No fluff
- No "looks good"
- Evidence required
- Separate fact vs inference
- Be brutally honest

and remember file by file and line by line
