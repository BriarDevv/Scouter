"""Regression tests for the on-startup janitor sweep.

Closes the gap documented in docs/audits/repo-deep-audit.md section 9:
post-crash recovery used to wait for the next beat tick (up to 15 min).
The FastAPI lifespan now fires the janitor sweep once at boot so crashed
tasks are surfaced immediately. A failure in the sweep must never prevent
the app from starting.
"""

from unittest.mock import patch


def test_startup_runs_sweep_stale_tasks():
    """Entering the FastAPI lifespan context must invoke sweep_stale_tasks once."""
    with patch("app.workers.janitor.sweep_stale_tasks") as mock_sweep:
        mock_sweep.return_value = {"tasks_failed": 0}
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app):
            pass

    mock_sweep.assert_called_once()


def test_startup_survives_sweep_exception():
    """A raising sweep must be logged but must NOT crash the app startup."""
    with patch(
        "app.workers.janitor.sweep_stale_tasks",
        side_effect=RuntimeError("DB unavailable"),
    ) as mock_sweep:
        from fastapi.testclient import TestClient

        from app.main import app

        # TestClient(app).__enter__ runs lifespan startup; if it raises, this
        # line will propagate. Assertion is implicit: block completes cleanly.
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    mock_sweep.assert_called_once()


def test_recovery_sweep_function_is_callable_directly():
    """The helper must also work outside the lifespan (e.g. from a CLI tool)."""
    with patch("app.workers.janitor.sweep_stale_tasks") as mock_sweep:
        mock_sweep.return_value = {
            "tasks_failed": 2,
            "pipelines_failed": 1,
            "pipelines_resumed": 1,
        }
        from app.main import _run_startup_recovery_sweep

        # Must not raise and must call the sweep.
        _run_startup_recovery_sweep()

    mock_sweep.assert_called_once()
