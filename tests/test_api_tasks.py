from sqlalchemy.exc import IntegrityError

from app.models.task_tracking import TaskRun
from app.services.task_tracking_service import queue_task_run
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
