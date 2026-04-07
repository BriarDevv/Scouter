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
from app.api.v1.scoring import get_rescore_all_status, rescore_all_leads, stop_rescore_all
from app.models.lead import Lead
from app.models.task_tracking import TaskRun
from app.models.territory import Territory
from app.services.pipeline.operational_task_service import (
    BATCH_PIPELINE_REDIS_KEY,
    BATCH_PIPELINE_SCOPE_KEY,
    RESCORE_ALL_SCOPE_KEY,
    get_batch_pipeline_status_snapshot,
    get_territory_crawl_status_snapshot,
    mark_batch_pipeline_legacy_stop_requested,
    mark_territory_crawl_legacy_stop_requested,
    serialize_batch_pipeline_status,
    serialize_rescore_all_status,
    serialize_territory_crawl_status,
    should_stop_operational_task,
)
from app.services.pipeline.task_tracking_service import get_task_run, request_task_stop
from app.workers.tasks import task_rescore_all


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


def test_batch_pipeline_status_snapshot_falls_back_to_legacy_mirror(db, monkeypatch):
    legacy = {
        "status": "running",
        "task_id": "legacy-batch-001",
        "processed": 3,
        "total": 9,
    }

    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service.load_legacy_operational_state",
        lambda redis_key: legacy if redis_key == BATCH_PIPELINE_REDIS_KEY else None,
    )

    payload = get_batch_pipeline_status_snapshot(db)

    assert payload["status"] == "running"
    assert payload["task_id"] == "legacy-batch-001"
    assert payload["processed"] == 3


def test_mark_legacy_stop_requested_updates_batch_and_crawl_payloads(monkeypatch):
    store = {
        BATCH_PIPELINE_REDIS_KEY: {"status": "running", "task_id": "legacy-batch-002"},
        "crawl:territory:territory-legacy": {
            "status": "running",
            "task_id": "legacy-crawl-001",
        },
    }

    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service.load_legacy_operational_state",
        lambda redis_key: store.get(redis_key),
    )
    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service.mirror_legacy_operational_state",
        lambda redis_key, payload, ttl_seconds=3600: store.__setitem__(redis_key, payload),
    )
    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service.delete_legacy_operational_state",
        lambda redis_key: store.pop(redis_key, None),
    )

    assert mark_batch_pipeline_legacy_stop_requested() is True
    assert mark_territory_crawl_legacy_stop_requested("territory-legacy") is True
    assert store[BATCH_PIPELINE_REDIS_KEY]["status"] == "stopping"
    assert store["crawl:territory:territory-legacy"]["status"] == "stopping"


def test_territory_crawl_status_snapshot_falls_back_to_legacy_mirror(db, monkeypatch):
    legacy = {
        "status": "running",
        "task_id": "legacy-crawl-002",
        "territory": "Centro",
        "current_city": "Cordoba",
    }

    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service.load_legacy_operational_state",
        lambda redis_key: legacy if redis_key == "crawl:territory:territory-legacy-002" else None,
    )

    payload = get_territory_crawl_status_snapshot(db, "territory-legacy-002")

    assert payload["status"] == "running"
    assert payload["task_id"] == "legacy-crawl-002"
    assert payload["current_city"] == "Cordoba"


def test_should_stop_operational_task_checks_canonical_and_legacy(db, monkeypatch):
    task_run = TaskRun(
        task_id="batch-task-stop-001",
        task_name="task_batch_pipeline",
        queue="default",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        status="running",
    )
    db.add(task_run)
    db.commit()

    request_task_stop(
        db,
        task_name="task_batch_pipeline",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
    )
    db.commit()

    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service._read_legacy_operational_state",
        lambda redis_key, suppress_errors: {"status": "running"},
    )

    assert should_stop_operational_task(
        task_id="batch-task-stop-001",
        redis_key=BATCH_PIPELINE_REDIS_KEY,
    ) is True
    assert should_stop_operational_task(
        task_id="missing-task-stop-001",
        redis_key=BATCH_PIPELINE_REDIS_KEY,
        treat_missing_legacy_as_stop=False,
    ) is False

    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service._read_legacy_operational_state",
        lambda redis_key, suppress_errors: None,
    )

    assert should_stop_operational_task(
        task_id="missing-task-stop-001",
        redis_key=BATCH_PIPELINE_REDIS_KEY,
        treat_missing_legacy_as_stop=True,
    ) is True

    def raise_redis_error(redis_key, suppress_errors):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(
        "app.services.pipeline.operational_task_service._read_legacy_operational_state",
        raise_redis_error,
    )

    assert should_stop_operational_task(
        task_id="missing-task-stop-001",
        redis_key=BATCH_PIPELINE_REDIS_KEY,
        treat_missing_legacy_as_stop=True,
    ) is False


def test_start_rescore_all_creates_canonical_task_run(db, monkeypatch):
    captured: dict[str, object] = {}

    def fake_delay(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(id="rescore-task-001")

    monkeypatch.setattr("app.workers.tasks.task_rescore_all.delay", fake_delay)

    payload = rescore_all_leads(
        request=SimpleNamespace(state=SimpleNamespace(correlation_id="corr-rescore-001")),
        db=db,
    )

    assert payload["task_id"] == "rescore-task-001"
    assert payload["status"] == "queued"
    assert payload["correlation_id"] == "corr-rescore-001"
    assert captured["kwargs"] == {"correlation_id": "corr-rescore-001"}

    task_run = get_task_run(db, "rescore-task-001")
    assert task_run is not None
    assert task_run.task_name == "task_rescore_all"
    assert task_run.scope_key == RESCORE_ALL_SCOPE_KEY
    assert task_run.current_step == "rescore_dispatch"


def test_rescore_all_status_and_stop_use_canonical_task_run(db):
    task_run = TaskRun(
        task_id="rescore-task-002",
        task_name="task_rescore_all",
        queue="default",
        scope_key=RESCORE_ALL_SCOPE_KEY,
        correlation_id="corr-rescore-002",
        status="running",
        current_step="rescore_scoring",
        progress_json={
            "total": 12,
            "rescored": 7,
            "errors": 2,
            "current_lead_id": "lead-123",
        },
    )
    db.add(task_run)
    db.commit()

    status_payload = get_rescore_all_status(db=db)
    assert status_payload["status"] == "running"
    assert status_payload["task_id"] == "rescore-task-002"
    assert status_payload["rescored"] == 7
    assert status_payload["errors"] == 2
    assert status_payload["current_lead_id"] == "lead-123"

    stop_payload = stop_rescore_all(db=db)
    assert stop_payload["ok"] is True

    refreshed = get_task_run(db, "rescore-task-002")
    assert refreshed is not None
    assert refreshed.status == "stopping"
    assert refreshed.stop_requested_at is not None


def test_serialize_rescore_all_status_maps_terminal_state():
    task_run = TaskRun(
        task_id="rescore-task-003",
        task_name="task_rescore_all",
        scope_key=RESCORE_ALL_SCOPE_KEY,
        status="succeeded",
        progress_json={
            "total": 5,
            "rescored": 4,
            "errors": 1,
        },
    )

    payload = serialize_rescore_all_status(task_run)

    assert payload["status"] == "done"
    assert payload["rescored"] == 4
    assert payload["errors"] == 1


def test_rescore_task_run_persists_canonical_progress(db, monkeypatch):
    lead_a = Lead(business_name="Lead A", city="Cordoba", score=10)
    lead_b = Lead(business_name="Lead B", city="Rosario", score=20)
    db.add_all([lead_a, lead_b])
    db.commit()

    def fake_score_lead(session, lead_id):
        lead = session.get(Lead, lead_id)
        lead.score = (lead.score or 0) + 1
        session.commit()
        return lead

    monkeypatch.setattr("app.workers.batch_tasks.score_lead", fake_score_lead)
    monkeypatch.setattr(
        "app.workers.batch_tasks.mirror_rescore_all_state",
        lambda *args, **kwargs: None,
    )

    result = task_rescore_all.run(correlation_id="corr-rescore-003")

    assert result["status"] == "done"
    assert result["rescored"] == 2

    task_run = (
        db.query(TaskRun)
        .filter(TaskRun.task_name == "task_rescore_all")
        .order_by(TaskRun.created_at.desc())
        .first()
    )
    assert task_run is not None
    assert task_run.scope_key == RESCORE_ALL_SCOPE_KEY
    assert task_run.status == "succeeded"
    assert task_run.correlation_id == "corr-rescore-003"
    assert task_run.progress_json["total"] == 2
    assert task_run.progress_json["rescored"] == 2
    assert task_run.progress_json["errors"] == 0
