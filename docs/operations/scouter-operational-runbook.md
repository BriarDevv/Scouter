# Scouter Operational Runbook

**Last updated:** 2026-04-05
**For:** Daily operator use

---

## 1. Normal Operation

**How to detect:** `make status` shows all green. `curl localhost:8000/health/detailed` returns all components OK. AI Office shows agents idle or active with recent decisions.

**What it means:** Pipeline processing leads, AI actors responding, no stuck runs.

**What to do:**
- Check AI Office 1-2x per day for new decisions, investigations, proposals
- Review pending ImprovementProposals from batch reviews (approve/reject)
- Check Performance > IA tab for health metrics
- Optionally trigger `make preflight` for full system check

**What NOT to do:**
- Don't restart services unnecessarily
- Don't re-run pipelines on already-processed leads without reason
- Don't approve proposals without reading the evidence summary

**Scaling:** In normal operation with RTX 4080 + 32GB, the system handles 4+ concurrent tasks. If lead volume is high, monitor Celery flower at `:5555` for queue backlog.

---

## 2. Degraded Operation

**How to detect:** `health/detailed` shows one component as "degraded". Common: Celery shows "Sin workers activos" (worker crashed or not started). Ollama shows high latency (>5s, model swapping).

**What it means:** System is partially functional. Pipelines may be slow or incomplete.

**What to do:**
- If Celery degraded: `make up` or restart worker manually
- If Ollama degraded: check `curl localhost:11434/api/tags` — if slow, a large model (27b) may be loading
- If Redis degraded: `docker compose up -d redis`
- If DB degraded: `docker compose up -d postgres`, check connection pool

**What NOT to do:**
- Don't trigger batch pipelines while degraded — they'll fail and create noise
- Don't approve proposals generated during degraded period (LLM may have used fallbacks)

**When to intervene:** If degraded state persists >5 minutes for Celery or >30 seconds for DB/Redis.

---

## 3. Blocked Pipelines

**How to detect:** AI Office shows a pipeline run with status "running" for >10 minutes. Or `GET /api/v1/pipelines/runs` shows runs with `finished_at: null` older than 10 min.

**What it means:** A pipeline step failed silently or the chain broke.

**What to do:**
1. Identify the stuck pipeline: `GET /api/v1/pipelines/runs?status=running`
2. Check current_step to see where it's stuck
3. Resume: `POST /api/v1/pipelines/runs/{id}/resume`
4. If resume fails, check worker logs: `tail -100 /tmp/scouter-worker.log`
5. If the lead already has all data (enriched, scored, analyzed), the idempotency guards will skip completed steps and chain forward

**What NOT to do:**
- Don't delete the PipelineRun record — it has tracking data
- Don't start a second pipeline for the same lead while one is stuck
- Don't restart the worker without first trying resume

**Recovery procedure:**
```bash
# Check stuck pipelines
curl -s localhost:8000/api/v1/pipelines/runs | python3 -c "
import sys,json
for r in json.load(sys.stdin):
    if r.get('status')=='running' and not r.get('finished_at'):
        print(f'STUCK: {r[\"id\"][:8]}... step={r.get(\"current_step\")}')
"

# Resume a stuck pipeline
curl -X POST localhost:8000/api/v1/pipelines/runs/{PIPELINE_ID}/resume
```

---

## 4. Batch Review Backlog

**How to detect:** `GET /api/v1/batch-reviews` shows multiple reviews with status "completed" and `proposals_pending > 0`.

**What it means:** Batch reviews are generating proposals faster than the operator is reviewing them.

**What to do:**
- Review proposals in priority order: HIGH impact first, then MEDIUM
- Reject proposals with LOW confidence — they're not worth the risk
- Approve proposals with HIGH confidence + HIGH impact — these are the highest-value changes
- For MEDIUM confidence proposals, check the evidence_summary before deciding

**What NOT to do:**
- Don't let proposals sit pending for >2 weeks — they become stale
- Don't approve everything blindly — the guardrails exist for a reason
- Don't ignore batch reviews — they're the system's learning mechanism

**Triage rules:**
| Impact | Confidence | Action |
|--------|-----------|--------|
| HIGH | HIGH | Approve (strong evidence) |
| HIGH | MEDIUM | Read evidence, decide |
| HIGH | LOW | Reject (insufficient evidence) |
| MEDIUM | HIGH | Approve |
| MEDIUM | MEDIUM | Read evidence, decide |
| MEDIUM/LOW | LOW | Reject |
| LOW | Any | Reject (not worth the risk) |

---

## 5. Proposal Approval Workflow

**When to approve:**
- The evidence summary cites specific metrics (not vague statements)
- The proposal aligns with what you're seeing operationally
- The confidence is MEDIUM or HIGH
- The category makes sense (scoring adjustment backed by outcome data)

**How to approve:**
```bash
curl -X POST localhost:8000/api/v1/batch-reviews/proposals/{PROPOSAL_ID}/approve
```
Or via the AI Office dashboard (when wired).

**After approval:** In v1, approved proposals are advisory — they don't auto-apply. The operator implements the change manually (adjust scoring weight, modify prompt, change channel default). Future versions may auto-apply LOW-risk proposals.

---

## 6. Proposal Rejection Workflow

**When to reject:**
- Evidence is weak or circular ("we recommend X because X seems good")
- Proposal contradicts known business reality
- Confidence is LOW
- The proposal would affect too many leads without enough data
- The proposal was already tried and didn't work

**How to reject:**
```bash
curl -X POST localhost:8000/api/v1/batch-reviews/proposals/{PROPOSAL_ID}/reject
```

**After rejection:** No system impact. The proposal is marked "rejected" and will not appear in future recommendations (unless new evidence supports it in a later batch review).

---

## 7. Guardrail Failure Response

**What guardrails exist:**
- Proposals requiring scoring weight changes need confidence >= "high"
- Proposals changing outreach channel defaults need 50+ outcomes
- No proposal auto-applies in v1
- Pipeline context size limits (2KB/step, 16KB total)
- Scout SSRF protection (private IP blocking)
- Prompt injection defense (anti-injection preamble)

**If a guardrail triggers:**
- The system logs it and continues operating
- The blocked action is recorded for operator review
- No manual intervention needed unless the guardrail itself is wrong

**If you think a guardrail is too strict:**
- Don't disable it directly
- Adjust thresholds in OperationalSettings via API or dashboard
- Example: lower `batch_review_outcome_threshold` from 5 to 3 if leads are slow

---

## 8. Operator Takeover Rules

**When to take over a Mote conversation:**
- Client asks a question Mote can't answer (pricing specifics, custom scope)
- Client objects strongly and Mote's response feels generic
- Client asks for a meeting — human should schedule directly
- Conversation has been going >5 exchanges without progress

**How to take over:**
```bash
curl -X POST localhost:8000/api/v1/ai-office/conversations/{CONVO_ID}/takeover
```

**When NOT to take over:**
- Client asks a simple question about services (Mote has the context)
- Client asks for portfolio (Mote can share the link)
- Client is just acknowledging a message

---

## 9. Recovery Procedures

### Pipeline stuck at enrichment/scoring/analysis
```bash
# Resume — idempotency guards will skip completed steps
curl -X POST localhost:8000/api/v1/pipelines/runs/{ID}/resume
```

### Worker crashed
```bash
make up  # Restarts all services including worker
# Or manually:
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 --queues=default,enrichment,scoring,llm,reviewer,research
```

### Ollama not responding
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
# If not responding, restart Ollama (Windows: restart the app)
# If in WSL: bash scripts/ensure-ollama-bridge.sh
```

### Batch review stuck at "generating"
```bash
# Check if the task is still running in Celery
# If stuck >10 min, the LLM likely failed
# Manual trigger will create a new review:
curl -X POST localhost:8000/api/v1/batch-reviews/generate
```

### Database connection errors
```bash
docker compose up -d postgres
# pool_pre_ping=True handles stale connections automatically
# If persistent, restart the API: make up
```

---

## 10. Known Blockers and Workarounds (until fixed)

### BLOCKER 1: Batch review proposals have no dashboard UI

**Current state:** Proposals exist in the API but there is no dashboard page to view or manage them.

**Workaround until fixed:**
```bash
# List batch reviews
curl -s localhost:8000/api/v1/batch-reviews | python3 -m json.tool

# View proposals for a specific review
curl -s localhost:8000/api/v1/batch-reviews/{REVIEW_ID} | python3 -m json.tool

# Approve a proposal
curl -X POST localhost:8000/api/v1/batch-reviews/proposals/{PROPOSAL_ID}/approve

# Reject a proposal
curl -X POST localhost:8000/api/v1/batch-reviews/proposals/{PROPOSAL_ID}/reject
```

**When checking:** After every 25 leads processed (or 10 HIGH), a batch review auto-triggers. Check periodically.

### BLOCKER 2: Approved proposals don't get applied

**Current state:** `approve_proposal()` sets status="approved" but nothing happens after. The `applied_at` and `result_notes` fields are dead.

**Workaround:** After approving a proposal, manually implement the recommended change:
- If category="scoring": manually adjust weights in code or settings
- If category="prompt": add hints to correction patterns (already auto-injected)
- If category="channel": manually change outreach defaults in settings
- If category="threshold": adjust threshold values in operational settings

**Track manually:** Note what you changed and when, so you can measure impact.

### BLOCKER 3: Research failures create pipeline zombies

**Current state:** If Scout/research returns non-completed status, the pipeline stays "running" forever.

**How to detect:**
```bash
# Find zombie pipelines (running for >10 min with no finish)
curl -s localhost:8000/api/v1/pipelines/runs | python3 -c "
import sys,json
for r in json.load(sys.stdin):
    if r.get('status')=='running' and not r.get('finished_at'):
        print(f'ZOMBIE: {r[\"id\"][:8]}... step={r.get(\"current_step\",\"?\")}')" 
```

**Workaround:** Resume the stuck pipeline — the idempotency guards will skip completed steps:
```bash
curl -X POST localhost:8000/api/v1/pipelines/runs/{PIPELINE_ID}/resume
```

If the pipeline is stuck at "research", the resume will chain to brief generation.

---

## 11. What Not To Do

- **Never** modify `.env` while services are running — restart after changes
- **Never** delete PipelineRun or TaskRun records — they're the audit trail
- **Never** approve all proposals at once without reading evidence
- **Never** run batch pipeline while another is running
- **Never** manually edit the `review_corrections` or `batch_reviews` tables
- **Never** skip the Reviewer step by disabling it permanently — it's the quality gate
- **Never** set `LOW_RESOURCE_MODE=true` on the RTX 4080 machine — it kills parallelism

---

## 11. Scaling Checklist

Before increasing automation level (safe → assisted → outreach → closer):

- [ ] At least 50 leads processed through full pipeline
- [ ] At least 1 batch review completed with proposals reviewed
- [ ] Approval rate of drafts > 70%
- [ ] Fallback rate < 10%
- [ ] At least 10 outcomes (WON/LOST) recorded
- [ ] Operator comfortable with Mote's response quality
- [ ] WhatsApp templates created and approved in Kapso
- [ ] Reviewed and understood the closer mode behavior
- [ ] Confirmed that manual takeover works in AI Office

**Scaling order:** safe → assisted (2+ weeks) → outreach (2+ weeks with templates) → closer (only after meeting rate proves outreach works)
