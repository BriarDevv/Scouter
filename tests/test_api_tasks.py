from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.lead import Lead
from app.models.task_tracking import TaskRun
from app.services.task_tracking_service import queue_task_run
from app.workers.tasks import _should_generate_draft
from tests.conftest import TestSessionLocal


def test_async_enrichment_status_endpoint(client):
    created = client.post("/api/v1/leads", json={"business_name": "Async Enrich", "city": "Cordoba"})
    lead_id = created.json()["id"]

    queued = client.post(f"/api/v1/enrichment/{lead_id}/async")
    assert queued.status_code == 200
    task_payload = queued.json()
    assert task_payload["status"] == "queued"
    assert task_payload["queue"] == "enrichment"
    assert task_payload["lead_id"] == lead_id
    assert task_payload["current_step"] == "enrichment"

    status = client.get(f"/api/v1/tasks/{task_payload['task_id']}/status")
    assert status.status_code == 200
    status_payload = status.json()
    assert status_payload["task_id"] == task_payload["task_id"]
    assert status_payload["status"] == "queued"
    assert status_payload["queue"] == "enrichment"
    assert status_payload["lead_id"] == lead_id
    assert status_payload["pipeline_run_id"] is None
    assert status_payload["current_step"] == "enrichment"


def test_pipeline_run_is_tracked_for_full_pipeline(client):
    created = client.post("/api/v1/leads", json={"business_name": "Pipeline Task", "city": "Mendoza"})
    lead_id = created.json()["id"]

    queued = client.post(f"/api/v1/scoring/{lead_id}/pipeline")
    assert queued.status_code == 200
    payload = queued.json()
    assert payload["status"] == "queued"
    assert payload["queue"] == "default"
    assert payload["lead_id"] == lead_id
    assert payload["pipeline_run_id"] is not None
    assert payload["current_step"] == "pipeline_dispatch"

    task_status = client.get(f"/api/v1/tasks/{payload['task_id']}/status")
    assert task_status.status_code == 200
    task_data = task_status.json()
    assert task_data["task_id"] == payload["task_id"]
    assert task_data["status"] == "queued"
    assert task_data["pipeline_run_id"] == payload["pipeline_run_id"]
    assert task_data["current_step"] == "pipeline_dispatch"

    pipeline_list = client.get(f"/api/v1/pipelines/runs?lead_id={lead_id}")
    assert pipeline_list.status_code == 200
    runs = pipeline_list.json()
    assert len(runs) == 1
    assert runs[0]["id"] == payload["pipeline_run_id"]
    assert runs[0]["status"] == "queued"

    pipeline_detail = client.get(f"/api/v1/pipelines/runs/{payload['pipeline_run_id']}")
    assert pipeline_detail.status_code == 200
    detail = pipeline_detail.json()
    assert detail["id"] == payload["pipeline_run_id"]
    assert detail["lead_id"] == lead_id
    assert detail["status"] == "queued"
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0]["task_id"] == payload["task_id"]

    task_list = client.get("/api/v1/tasks?status=queued")
    assert task_list.status_code == 200
    tasks = task_list.json()
    assert any(task["task_id"] == payload["task_id"] for task in tasks)


def test_queue_task_run_handles_worker_race(db, monkeypatch):
    task_id = "race-task-id"
    real_commit = db.commit
    commit_calls = {"count": 0}

    def fake_commit():
        commit_calls["count"] += 1
        if commit_calls["count"] == 1:
            db.rollback()
            other = TestSessionLocal()
            try:
                other.add(
                    TaskRun(
                        task_id=task_id,
                        task_name="task_full_pipeline",
                        queue="default",
                        status="running",
                        current_step="pipeline_dispatch",
                    )
                )
                other.commit()
            finally:
                other.close()
            raise IntegrityError("insert", {}, Exception("duplicate task_id"))
        return real_commit()

    monkeypatch.setattr(db, "commit", fake_commit)

    task_run = queue_task_run(
        db,
        task_id=task_id,
        task_name="task_full_pipeline",
        queue="default",
        current_step="pipeline_dispatch",
    )

    assert task_run.task_id == task_id
    assert task_run.status == "running"
    assert task_run.current_step == "pipeline_dispatch"


def test_draft_skipped_when_quality_not_high(db):
    """Draft generation should be skipped when lead quality is not 'high'."""
    lead = Lead(business_name="Low Quality Lead", city="Rosario", email="test@example.com")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    # quality not set -> should not generate
    assert _should_generate_draft(lead) is False

    lead.llm_quality = "medium"
    db.commit()
    assert _should_generate_draft(lead) is False

    lead.llm_quality = "low"
    db.commit()
    assert _should_generate_draft(lead) is False

    lead.llm_quality = "unknown"
    db.commit()
    assert _should_generate_draft(lead) is False

    lead.llm_quality = "high"
    db.commit()
    assert _should_generate_draft(lead) is True


def test_draft_skipped_when_no_email(db):
    """Draft generation should be skipped when lead has no email even if high quality."""
    lead = Lead(business_name="No Email Lead", city="CABA")
    db.add(lead)
    db.commit()

    lead.llm_quality = "high"
    db.commit()
    assert _should_generate_draft(lead) is False

    lead.email = "contact@business.com"
    db.commit()
    assert _should_generate_draft(lead) is True


def test_janitor_marks_stale_tasks_as_failed(db):
    """Janitor should mark tasks stuck > 10 min as failed."""
    stale_task = TaskRun(
        task_id="stale-test-001",
        task_name="task_analyze_lead",
        queue="llm",
        status="running",
        current_step="analysis",
    )
    db.add(stale_task)
    db.commit()

    # Use raw SQL to bypass onupdate=func.now()
    db.execute(
        text("UPDATE task_runs SET updated_at = :ts WHERE task_id = :tid"),
        {"ts": datetime.now(UTC) - timedelta(minutes=15), "tid": "stale-test-001"},
    )
    db.commit()

    from app.workers.janitor import sweep_stale_tasks
    result = sweep_stale_tasks(session_factory=TestSessionLocal)

    db.expire_all()
    db.refresh(stale_task)
    assert stale_task.status == "failed"
    assert "stale" in stale_task.error.lower()
    assert result["tasks_failed"] >= 1
