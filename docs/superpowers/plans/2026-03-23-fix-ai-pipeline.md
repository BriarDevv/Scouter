# Fix AI Pipeline — Stuck Tasks, Conditional Drafts & Reliability

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the root cause of stuck tasks in the AI pipeline, make draft generation conditional on lead quality, and add reliability guardrails (timeouts, janitor, concurrency).

**Architecture:** The Celery worker currently only consumes the `default` queue, so tasks routed to `enrichment`, `scoring`, `llm`, and `reviewer` queues are never picked up. We fix this at the worker startup level, add soft time limits to LLM tasks, gate draft generation on quality="high", and add a periodic janitor to recover stale tasks.

**Tech Stack:** Python 3.12, Celery 5.x, Redis, SQLAlchemy, FastAPI, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `scripts/clawscout.sh:82` | Worker startup command — add `-Q` flag |
| Modify | `app/workers/celery_app.py:11-36` | Celery config — timeouts, rate limit, beat schedule |
| Modify | `app/workers/tasks.py:242-340` | `task_analyze_lead` — persist quality on Lead model |
| Modify | `app/workers/tasks.py:342-424` | `task_generate_draft` — skip if quality != "high" |
| Modify | `app/workers/tasks.py:787-874` | `task_full_pipeline` — pass quality via chain |
| Create | `app/workers/janitor.py` | Periodic task to mark stale tasks as failed |
| Modify | `app/models/lead.py` | Add `llm_quality` column to Lead |
| Create | `alembic/versions/xxxx_add_llm_quality.py` | Migration for new column |
| Test | `tests/test_api_tasks.py` | Add tests for conditional draft + stale recovery |

---

### Task 1: Fix worker queue subscription

The root cause of all stuck tasks. The worker starts without `-Q`, so it only consumes `default`. Tasks routed to `enrichment`, `scoring`, `llm`, `reviewer` sit forever.

**Files:**
- Modify: `scripts/clawscout.sh:82`

- [ ] **Step 1: Edit the worker startup command**

In `scripts/clawscout.sh`, find line 82:
```bash
        nohup celery -A app.workers.celery_app worker \
            --loglevel=info --concurrency=2 \
```

Replace with:
```bash
        nohup celery -A app.workers.celery_app worker \
            --loglevel=info --concurrency=4 \
            -Q default,enrichment,scoring,llm,reviewer \
```

This makes the single worker consume ALL defined queues and bumps concurrency from 2 to 4.

- [ ] **Step 2: Verify the fix locally**

Run:
```bash
cd /home/briar/src/ClawScout && make down && make up
```

Then check worker logs:
```bash
tail -20 logs/worker.log
```

Expected: Worker output shows `[queues] ... default,enrichment,scoring,llm,reviewer` in the startup banner.

- [ ] **Step 3: Smoke test — trigger a pipeline and confirm it progresses**

```bash
# Create a lead and run the pipeline
curl -s -X POST http://localhost:8000/api/v1/leads -H 'Content-Type: application/json' \
  -d '{"business_name":"Test Queue Fix","city":"CABA"}' | python3 -m json.tool

# Use the returned lead_id:
curl -s -X POST http://localhost:8000/api/v1/scoring/<LEAD_ID>/pipeline | python3 -m json.tool
```

Check the task status after a few seconds — it should NOT be "stale":
```bash
curl -s http://localhost:8000/api/v1/tasks/<TASK_ID>/status | python3 -m json.tool
```

Expected: status progresses through `running` steps, not stuck.

- [ ] **Step 4: Commit**

```bash
git add scripts/clawscout.sh
git commit -m "fix: worker consumes all queues — resolves stuck tasks

The worker was started without -Q, so it only consumed the 'default'
queue. Tasks routed to enrichment/scoring/llm/reviewer were never
picked up. Also bumps concurrency from 2 to 4."
```

---

### Task 2: Add soft time limits to LLM tasks

LLM calls (Ollama) can hang indefinitely. Without a timeout, the task stays in `running` forever and blocks a worker slot.

**Files:**
- Modify: `app/workers/celery_app.py:11-36`
- Modify: `app/workers/tasks.py:242` (task_analyze_lead decorator)
- Modify: `app/workers/tasks.py:342` (task_generate_draft decorator)

- [ ] **Step 1: Add global soft time limit to celery config**

In `app/workers/celery_app.py`, add inside `celery_app.conf.update(...)`:
```python
    # Timeouts — prevent tasks from hanging indefinitely
    task_soft_time_limit=300,   # 5 min soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=360,        # 6 min hard kill
```

- [ ] **Step 2: Add explicit soft_time_limit on LLM task decorators**

In `app/workers/tasks.py`, update both decorators:

Line 242:
```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, soft_time_limit=300, time_limit=360)
```

Line 342:
```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, soft_time_limit=300, time_limit=360)
```

- [ ] **Step 3: Handle SoftTimeLimitExceeded in the except blocks**

The existing `except Exception` blocks already call `_track_failure` and `self.retry`, which will handle `SoftTimeLimitExceeded` correctly (it inherits from `Exception` in Celery 5). No additional code needed — just verify the import exists. The retry mechanism will attempt up to `max_retries=2` times before marking as failed.

- [ ] **Step 4: Commit**

```bash
git add app/workers/celery_app.py app/workers/tasks.py
git commit -m "fix: add 5min soft time limit to LLM tasks

Prevents Ollama calls from hanging indefinitely and blocking
worker slots. Global 5min soft / 6min hard limit, plus explicit
limits on task_analyze_lead and task_generate_draft."
```

---

### Task 3: Persist quality on Lead and make draft conditional

Currently `task_analyze_lead` returns `quality` in its result dict but doesn't persist it on the Lead. `task_generate_draft` always runs regardless. We need to: (a) persist quality, (b) skip draft if quality != "high".

**Files:**
- Modify: `app/models/lead.py` — add `llm_quality` column
- Create: migration via alembic
- Modify: `app/workers/tasks.py:307-310` — persist quality in analyze task
- Modify: `app/workers/tasks.py:354-384` — check quality in draft task
- Test: `tests/test_api_tasks.py`

- [ ] **Step 1: Write failing test for conditional draft**

Add to `tests/test_api_tasks.py`:

```python
def test_draft_skipped_when_quality_not_high(db):
    """Draft generation should be skipped when lead quality is not 'high'."""
    from app.models.lead import Lead

    lead = Lead(business_name="Low Quality Lead", city="Rosario")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # Simulate analysis result: quality = "medium"
    lead.llm_quality = "medium"
    db.commit()

    from app.services.outreach_service import generate_outreach_draft
    from unittest.mock import patch

    with patch("app.workers.tasks.generate_outreach_draft") as mock_gen:
        # Import and call the inner logic directly
        from app.workers.tasks import _should_generate_draft
        assert _should_generate_draft(lead) is False

    # Now test with "high"
    lead.llm_quality = "high"
    db.commit()
    assert _should_generate_draft(lead) is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/briar/src/ClawScout && python -m pytest tests/test_api_tasks.py::test_draft_skipped_when_quality_not_high -v
```

Expected: FAIL — `llm_quality` attribute doesn't exist, `_should_generate_draft` doesn't exist.

- [ ] **Step 3: Add `llm_quality` column to Lead model**

In `app/models/lead.py`, add the column (near other `llm_*` fields):
```python
    llm_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

- [ ] **Step 4: Create alembic migration**

```bash
cd /home/briar/src/ClawScout
source .venv/bin/activate
alembic revision --autogenerate -m "add llm_quality to leads"
alembic upgrade head
```

- [ ] **Step 5: Persist quality in `task_analyze_lead`**

In `app/workers/tasks.py`, after line 308 (`lead.llm_suggested_angle = ...`), add:
```python
            lead.llm_quality = evaluation["quality"]
```

Also add it in `task_batch_pipeline` (around line 976), after the equivalent `lead.llm_suggested_angle` line:
```python
                lead.llm_quality = evaluation["quality"]
```

- [ ] **Step 6: Add `_should_generate_draft` helper and gate `task_generate_draft`**

In `app/workers/tasks.py`, add the helper function before `task_generate_draft` (around line 341):
```python
def _should_generate_draft(lead: Lead) -> bool:
    """Only generate outreach drafts for high-quality leads."""
    return getattr(lead, "llm_quality", None) == "high"
```

Then in `task_generate_draft`, after loading the lead (around line 374), add the quality gate:
```python
            lead = db.get(Lead, uuid.UUID(lead_id))
            if not lead:
                # ... existing not_found handling ...

            if not _should_generate_draft(lead):
                result = {
                    "status": "skipped",
                    "lead_id": lead_id,
                    "reason": f"quality={lead.llm_quality!r}, draft only for high",
                }
                mark_task_succeeded(
                    db,
                    task_id=task_id,
                    result=result,
                    current_step="draft_generation",
                    pipeline_run_id=pipeline_uuid,
                    pipeline_status="succeeded" if pipeline_uuid else None,
                )
                if pipeline_uuid:
                    with SessionLocal() as pipeline_db:
                        from app.services.task_tracking_service import update_pipeline_run
                        update_pipeline_run(
                            pipeline_db,
                            pipeline_uuid,
                            current_step="completed",
                            status="succeeded",
                            result=result,
                            finished=True,
                        )
                logger.info("draft_skipped_quality_gate", lead_id=lead_id, quality=lead.llm_quality)
                return result

            draft = generate_outreach_draft(db, uuid.UUID(lead_id))
```

Also gate the batch pipeline (around line 979):
```python
                # Step 4: Generate draft (only for high quality)
                progress["current_step"] = "draft"
                redis.set(redis_key, _json.dumps(progress), ex=3600)
                if lead.llm_quality == "high":
                    generate_draft_content(lead, db=db)
                else:
                    logger.info("batch_draft_skipped", lead=lead.business_name, quality=lead.llm_quality)
```

- [ ] **Step 7: Run the test**

```bash
python -m pytest tests/test_api_tasks.py::test_draft_skipped_when_quality_not_high -v
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add app/models/lead.py app/workers/tasks.py alembic/versions/*llm_quality* tests/test_api_tasks.py
git commit -m "feat: draft generation gated on llm_quality='high'

Persists quality evaluation result on Lead.llm_quality. Draft
generation (both async pipeline and batch) now skips leads that
are not high quality. Marks the task as succeeded with status
'skipped' so the pipeline completes cleanly."
```

---

### Task 4: Add stale task janitor

The current stale detection in `_merge_task_view` is read-only — it just changes the label in API responses. We need a periodic task that actually marks stale tasks as failed so the system recovers.

**Files:**
- Create: `app/workers/janitor.py`
- Modify: `app/workers/celery_app.py` — add beat schedule
- Modify: `scripts/clawscout.sh` — start celery beat alongside worker
- Test: `tests/test_api_tasks.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_api_tasks.py`:

```python
def test_janitor_marks_stale_tasks_as_failed(db):
    """Janitor should mark tasks stuck > 10 min as failed."""
    from datetime import UTC, datetime, timedelta
    from app.models.task_tracking import TaskRun

    stale_task = TaskRun(
        task_id="stale-test-001",
        task_name="task_analyze_lead",
        queue="llm",
        status="running",
        current_step="analysis",
    )
    db.add(stale_task)
    db.commit()

    # Manually backdate updated_at to 15 minutes ago
    stale_task.updated_at = datetime.now(UTC) - timedelta(minutes=15)
    db.commit()

    from app.workers.janitor import sweep_stale_tasks
    result = sweep_stale_tasks()

    db.refresh(stale_task)
    assert stale_task.status == "failed"
    assert "stale" in stale_task.error.lower()
    assert result["marked_failed"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_api_tasks.py::test_janitor_marks_stale_tasks_as_failed -v
```

Expected: FAIL — `app.workers.janitor` module doesn't exist.

- [ ] **Step 3: Create `app/workers/janitor.py`**

```python
"""Periodic janitor — marks stale tasks as failed so the system recovers."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.task_tracking import TaskRun
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

STALE_THRESHOLD = timedelta(minutes=10)
ACTIVE_STATUSES = ("running", "queued", "retrying")


def sweep_stale_tasks() -> dict:
    """Find tasks stuck in active status > STALE_THRESHOLD and mark them failed."""
    cutoff = datetime.now(UTC) - STALE_THRESHOLD

    with SessionLocal() as db:
        stale = db.execute(
            select(TaskRun).where(
                TaskRun.status.in_(ACTIVE_STATUSES),
                TaskRun.updated_at < cutoff,
            )
        ).scalars().all()

        count = 0
        for task_run in stale:
            task_run.status = "failed"
            task_run.error = f"Stale: no progress for >{STALE_THRESHOLD.total_seconds() / 60:.0f} min — marked failed by janitor"
            task_run.finished_at = datetime.now(UTC)
            count += 1
            logger.warning(
                "janitor_marked_stale",
                task_id=task_run.task_id,
                task_name=task_run.task_name,
                last_updated=str(task_run.updated_at),
            )

        if count:
            db.commit()

    result = {"marked_failed": count}
    logger.info("janitor_sweep_done", **result)
    return result


@celery_app.task(name="app.workers.janitor.task_sweep_stale")
def task_sweep_stale() -> dict:
    """Celery-wrapped janitor for use with celery beat."""
    return sweep_stale_tasks()
```

- [ ] **Step 4: Add beat schedule to celery config**

In `app/workers/celery_app.py`, add to `celery_app.conf.update(...)`:
```python
    # Beat schedule — periodic maintenance
    beat_schedule={
        "sweep-stale-tasks": {
            "task": "app.workers.janitor.task_sweep_stale",
            "schedule": 300.0,  # every 5 minutes
        },
    },
```

Also update `autodiscover_tasks` to include janitor:
```python
celery_app.autodiscover_tasks(["app.workers", "app.workers.janitor"])
```

- [ ] **Step 5: Add celery beat to clawscout.sh**

In `scripts/clawscout.sh`, after the worker startup block (after `log_ok "Worker corriendo"` around line 89), add:

```bash
    # 2b. Celery beat (scheduler)
    if is_running beat; then
        log_ok "Beat ya esta corriendo (PID $(get_pid beat))"
    else
        log_info "Iniciando Celery beat..."
        nohup celery -A app.workers.celery_app beat \
            --loglevel=info \
            >>"$LOG_DIR/beat.log" 2>&1 &
        echo $! > "$PID_DIR/beat.pid"
        sleep 2
        if is_running beat; then
            log_ok "Beat corriendo (PID $(get_pid beat))"
        else
            log_warn "Beat no arranco — ver logs/beat.log"
        fi
    fi
```

And in `cmd_stop`, add beat shutdown before the worker block:
```bash
    # Beat
    if is_running beat; then
        local pid
        pid=$(get_pid beat)
        kill "$pid" 2>/dev/null || true
        rm -f "$PID_DIR/beat.pid"
        log_ok "Beat detenido (was PID $pid)"
    else
        log_info "Beat no estaba corriendo"
    fi
```

And in `cmd_status`, add:
```bash
    # Celery beat
    if is_running beat; then
        log_ok "beat corriendo (PID $(get_pid beat))"
    else
        log_fail "beat no esta corriendo"
    fi
```

- [ ] **Step 6: Run the test**

```bash
python -m pytest tests/test_api_tasks.py::test_janitor_marks_stale_tasks_as_failed -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/workers/janitor.py app/workers/celery_app.py scripts/clawscout.sh tests/test_api_tasks.py
git commit -m "feat: add stale task janitor with celery beat

Periodic task runs every 5 min, finds tasks stuck in active status
for >10 min, and marks them as failed. Previously stale detection
was read-only in the API response. Also starts celery beat in
clawscout.sh."
```

---

### Task 5: Relax rate limit

The current `task_default_rate_limit="10/m"` is very restrictive for LLM tasks. With concurrency=4 and tasks that take a few seconds each, this creates unnecessary queuing.

**Files:**
- Modify: `app/workers/celery_app.py:18`

- [ ] **Step 1: Remove the global rate limit**

In `app/workers/celery_app.py`, change:
```python
    task_default_rate_limit="10/m",
```
to:
```python
    task_default_rate_limit=None,  # No global rate limit; per-task limits if needed
```

The individual tasks can add their own `rate_limit` in their decorator if needed (e.g., to avoid hammering an external API), but a blanket 10/m on all tasks is a bottleneck.

- [ ] **Step 2: Commit**

```bash
git add app/workers/celery_app.py
git commit -m "fix: remove 10/m global rate limit

The blanket rate limit was throttling all tasks unnecessarily.
Individual tasks can set their own rate_limit if needed."
```

---

## Summary of changes

| Fix | Impact | Risk |
|-----|--------|------|
| `-Q default,enrichment,scoring,llm,reviewer` | Resolves ALL stuck tasks | Low — just enables existing queues |
| `soft_time_limit=300` | Prevents hung LLM calls from blocking workers | Low — 5 min is generous for Ollama |
| `llm_quality` gate on drafts | Drafts only for high-quality leads | Medium — needs migration |
| Janitor + celery beat | Auto-recovers stale tasks | Low — marks as failed, doesn't retry |
| Remove rate limit, concurrency=4 | Better throughput | Low — was artificially constrained |
