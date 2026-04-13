"""Celery task metrics collected via signals."""

from collections import defaultdict
from threading import Lock

from celery.signals import task_failure, task_retry, task_success

_lock = Lock()
_counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))


@task_success.connect
def _on_success(sender=None, **kwargs):
    with _lock:
        _counters[sender]["success"] += 1


@task_failure.connect
def _on_failure(sender=None, **kwargs):
    with _lock:
        _counters[sender]["failure"] += 1


@task_retry.connect
def _on_retry(sender=None, **kwargs):
    with _lock:
        _counters[sender]["retry"] += 1


def get_task_metrics() -> dict:
    with _lock:
        return dict(_counters)


def get_queue_depths() -> dict[str, int]:
    """Get current queue depths from Redis."""
    from app.workers.celery_app import celery_app

    try:
        inspector = celery_app.control.inspect(timeout=2)
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        total_active = sum(len(tasks) for tasks in active.values())
        total_reserved = sum(len(tasks) for tasks in reserved.values())
        return {"active": total_active, "reserved": total_reserved}
    except Exception:
        return {"active": -1, "reserved": -1}
