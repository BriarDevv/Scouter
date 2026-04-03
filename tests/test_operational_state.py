import uuid
from types import SimpleNamespace

from app.api.v1.crawl import (
    TerritoryCrawlRequest,
    get_territory_crawl_status,
    start_territory_crawl,
    stop_territory_crawl,
)
from app.api.v1.pipelines import (
    get_batch_pipeline_status,
    start_batch_pipeline,
    stop_batch_pipeline,
)
from app.models.task_tracking import TaskRun
from app.models.territory import Territory
from app.services.operational_task_service import (
    BATCH_PIPELINE_SCOPE_KEY,
    serialize_batch_pipeline_status,
    serialize_territory_crawl_status,
)
from app.services.task_tracking_service import get_task_run, request_task_stop


def test_start_batch_pipeline_creates_canonical_task_run(db, monkeypatch):
    captured: dict[str, object] = {}

    def fake_delay(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(id="batch-task-001")

    monkeypatch.setattr("app.workers.tasks.task_batch_pipeline.delay", fake_delay)

    payload = start_batch_pipeline(
        request=SimpleNamespace(state=SimpleNamespace(correlation_id="corr-batch-001")),
        db=db,
    )

    assert payload["ok"] is True
    assert captured["kwargs"] == {"status_filter": "new", "correlation_id": "corr-batch-001"}

    task_run = get_task_run(db, "batch-task-001")
    assert task_run is not None
    assert task_run.task_name == "task_batch_pipeline"
    assert task_run.scope_key == BATCH_PIPELINE_SCOPE_KEY
    assert task_run.correlation_id == "corr-batch-001"
    assert task_run.current_step == "batch_dispatch"


def test_batch_pipeline_status_and_stop_use_canonical_task_run(db):
    task_run = TaskRun(
        task_id="batch-task-002",
        task_name="task_batch_pipeline",
        queue="default",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        correlation_id="corr-batch-002",
        status="running",
        current_step="analysis",
        progress_json={
            "total": 10,
            "processed": 4,
            "current_lead": "Acme",
            "errors": 1,
            "crawl_rounds": 1,
            "leads_from_crawl": 6,
        },
    )
    db.add(task_run)
    db.commit()

    status_payload = get_batch_pipeline_status(db=db)
    assert status_payload["status"] == "running"
    assert status_payload["task_id"] == "batch-task-002"
    assert status_payload["processed"] == 4
    assert status_payload["current_lead"] == "Acme"
    assert status_payload["correlation_id"] == "corr-batch-002"

    stop_payload = stop_batch_pipeline(db=db)
    assert stop_payload["ok"] is True

    refreshed = get_task_run(db, "batch-task-002")
    assert refreshed is not None
    assert refreshed.status == "stopping"
    assert refreshed.stop_requested_at is not None


def test_start_territory_crawl_creates_canonical_task_run(db, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.GOOGLE_MAPS_API_KEY", "AIzaSy1234567890")

    territory = Territory(name="Centro", cities=["Cordoba", "Villa Carlos Paz"])
    db.add(territory)
    db.commit()
    db.refresh(territory)

    captured: dict[str, object] = {}

    def fake_delay(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(id="crawl-task-001")

    monkeypatch.setattr("app.workers.tasks.task_crawl_territory.delay", fake_delay)

    payload = start_territory_crawl(
        body=TerritoryCrawlRequest(territory_id=str(territory.id)),
        request=SimpleNamespace(state=SimpleNamespace(correlation_id="corr-crawl-001")),
        db=db,
    )

    assert payload["ok"] is True
    assert captured["kwargs"]["territory_id"] == str(territory.id)
    assert captured["kwargs"]["correlation_id"] == "corr-crawl-001"

    task_run = get_task_run(db, "crawl-task-001")
    assert task_run is not None
    assert task_run.task_name == "task_crawl_territory"
    assert task_run.scope_key == str(territory.id)
    assert task_run.correlation_id == "corr-crawl-001"


def test_territory_crawl_status_and_stop_use_canonical_task_run(db):
    territory_id = str(uuid.uuid4())
    task_run = TaskRun(
        task_id="crawl-task-002",
        task_name="task_crawl_territory",
        queue="default",
        scope_key=territory_id,
        correlation_id="corr-crawl-002",
        status="running",
        current_step="crawling",
        progress_json={
            "territory": "Norte",
            "total_cities": 3,
            "current_city_idx": 2,
            "current_city": "Salta",
            "leads_found": 15,
            "leads_created": 7,
            "leads_skipped": 8,
        },
    )
    db.add(task_run)
    db.commit()

    status_payload = get_territory_crawl_status(territory_id=territory_id, db=db)
    assert status_payload["status"] == "running"
    assert status_payload["task_id"] == "crawl-task-002"
    assert status_payload["current_city"] == "Salta"
    assert status_payload["leads_created"] == 7

    stop_payload = stop_territory_crawl(territory_id=territory_id, db=db)
    assert stop_payload["ok"] is True

    refreshed = get_task_run(db, "crawl-task-002")
    assert refreshed is not None
    assert refreshed.status == "stopping"
    assert refreshed.stop_requested_at is not None


def test_operational_serializers_map_terminal_states():
    batch_done = TaskRun(
        task_id="batch-task-003",
        task_name="task_batch_pipeline",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        status="succeeded",
        progress_json={"processed": 8, "total": 8},
    )
    crawl_failed = TaskRun(
        task_id="crawl-task-003",
        task_name="task_crawl_territory",
        scope_key=str(uuid.uuid4()),
        status="failed",
        error="boom",
        progress_json={"territory": "Sur"},
    )

    batch_payload = serialize_batch_pipeline_status(batch_done)
    crawl_payload = serialize_territory_crawl_status(crawl_failed)

    assert batch_payload["status"] == "done"
    assert batch_payload["processed"] == 8
    assert crawl_payload["status"] == "error"
    assert crawl_payload["error"] == "boom"


def test_request_task_stop_marks_scoped_task_run(db):
    task_run = TaskRun(
        task_id="crawl-task-004",
        task_name="task_crawl_territory",
        queue="default",
        scope_key="territory-004",
        status="running",
        current_step="crawling",
    )
    db.add(task_run)
    db.commit()

    stopped = request_task_stop(
        db,
        task_name="task_crawl_territory",
        scope_key="territory-004",
    )

    assert stopped is not None
    assert stopped.status == "stopping"
    assert stopped.stop_requested_at is not None
