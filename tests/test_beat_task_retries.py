"""Regression tests for beat-scheduled task retry policies.

Fixes the gap documented in docs/audits/repo-deep-audit.md section 6:
previously task_auto_process_new_leads had max_retries=0 and
task_growth_cycle swallowed exceptions, so a transient broker/DB hiccup
would silently lose up to 30 minutes of work.

Acceptance: each beat-scheduled task must have
  - max_retries >= 2
  - autoretry_for containing Exception (so retries fire on any failure)
"""

from app.workers.auto_pipeline_tasks import task_auto_process_new_leads
from app.workers.growth_tasks import task_growth_cycle
from app.workers.inbox_tasks import task_sync_inbound_mail


def _assert_retry_policy(task, *, expected_max_retries: int = 2) -> None:
    assert task.max_retries == expected_max_retries, (
        f"{task.name}: expected max_retries={expected_max_retries}, got {task.max_retries}"
    )
    autoretry_for = getattr(task, "autoretry_for", None) or ()
    assert Exception in autoretry_for, (
        f"{task.name}: autoretry_for must contain Exception, got {autoretry_for}"
    )
    # retry_backoff should be truthy (bool True or an int count of seconds)
    assert getattr(task, "retry_backoff", None), (
        f"{task.name}: retry_backoff must be enabled to prevent hot-retry loops"
    )


def test_auto_process_new_leads_has_retries():
    _assert_retry_policy(task_auto_process_new_leads)


def test_sync_inbound_mail_has_retries():
    _assert_retry_policy(task_sync_inbound_mail)


def test_growth_cycle_has_retries():
    _assert_retry_policy(task_growth_cycle)
