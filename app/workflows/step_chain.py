"""Canonical pipeline step chain used by the janitor and the resume endpoint.

Single source of truth for "given a pipeline's current_step, which Celery
task should fire to continue the pipeline?". Avoids the drift that used
to exist between:

- app/workers/janitor.py (auto-resume of retryable failures)
- app/api/v1/pipelines.py POST /runs/{id}/resume (manual resume endpoint)

Both callers import PIPELINE_STEP_CHAIN from here.

Contract:
- Keys are values of `PipelineRun.current_step` set by each task before it
  begins work (see tracked_task_step in app/services/pipeline/...).
- Values are the task attribute names exposed on the `app.workers.tasks`
  shim module (NOT the dotted celery task name), since callers do
  `getattr(task_module, next_task_name)`.
- A value of None means "terminal step, nothing to resume".
"""

from __future__ import annotations

from typing import Final

PIPELINE_STEP_CHAIN: Final[dict[str, str | None]] = {
    "pipeline_dispatch": "task_enrich_lead",
    "enrichment": "task_score_lead",
    "scoring": "task_analyze_lead",
    # Re-trigger analysis so the branch decision (HIGH → research, else →
    # draft) is re-evaluated against current lead state.
    "analysis": "task_analyze_lead",
    "research": "task_generate_brief",
    # Scout failure: skip to brief so the pipeline does not starve on an
    # optional enrichment step.
    "scout": "task_generate_brief",
    "brief_generation": "task_review_brief",
    "brief_review": "task_generate_draft",
    "draft_generation": None,
}
