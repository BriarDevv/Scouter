Create a new Celery task for Scouter.

The user will provide: task purpose, domain, and what it should do.

## Checklist

1. **Choose the right file** in `app/workers/`:
   - Name it `{domain}_tasks.py` (e.g., `notification_tasks.py`)
   - Check if a domain file already exists before creating a new one
   - **NEVER add tasks to `tasks.py`** — that is a deprecated re-export shim
2. **Define the task** using `@celery_app.task()`:
   - `name="app.workers.tasks.task_{action}_{resource}"` (keep the `tasks.` prefix for backward compat)
   - `bind=True` to access `self.request`
   - Set `max_retries`, `default_retry_delay`, `soft_time_limit` as appropriate
3. **Use `tracked_task_step`** for pipeline-aware tasks:
   - Import from `app.services.pipeline.task_tracking_service`
   - Wrap the main logic in `with tracked_task_step(db, task_id, lead_id, step_name, queue, pipeline_uuid):`
4. **Use `SessionLocal`** for DB access (not dependency injection):
   - `from app.db.session import SessionLocal`
   - `with SessionLocal() as db:`
5. **Register the queue** if new — add to the worker startup command in `scripts/scouter.sh` `-Q` flag
6. **Add re-export** to `app/workers/tasks.py` if external code needs backward-compatible imports

## Conventions

- Logging: `logger = get_logger(__name__)` — structured, no f-strings
- Error handling: catch `SoftTimeLimitExceeded` explicitly, use `_track_failure` helper
- Task IDs: `str(self.request.id)` or `_request_task_id(self.request)`
- Pipeline context: accept `pipeline_run_id: str | None = None` and `correlation_id: str | None = None`
- Queue routing: use `_queue_name(self.request, "domain")` helper

## Patterns to follow

- Simple pipeline task: `app/workers/pipeline_tasks.py` (`task_enrich_lead`)
- Research with timeout: `app/workers/research_tasks.py` (`task_research_lead`)
- Batch processing: `app/workers/batch_tasks.py`
- Periodic cleanup: `app/workers/janitor.py`

## After creation

Run:
```bash
make test    # Verify nothing broke
make lint    # Check style
```
