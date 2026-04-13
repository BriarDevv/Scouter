from app.services.pipeline.task_tracking_service import get_task_run
from app.workers.crawl_tasks import task_crawl_territory
from app.workflows.territory_crawl import run_territory_crawl_workflow


def test_run_territory_crawl_workflow_persists_canonical_state(db, monkeypatch):
    from app.models.territory import Territory

    territory = Territory(name="Centro", cities=["Cordoba"])
    db.add(territory)
    db.commit()
    db.refresh(territory)

    mirrored: list[dict] = []

    class FakeCrawler:
        def crawl(self, **kwargs):
            return []

    monkeypatch.setattr(
        "app.workflows.territory_crawl.should_stop_operational_task",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        "app.workflows.territory_crawl.GoogleMapsCrawler",
        lambda: FakeCrawler(),
    )
    # Stub the effective-key resolver so the workflow doesn't short-circuit
    # on the "no API key configured" guard. The FakeCrawler ignores the key
    # anyway — this is just to clear the precondition.
    monkeypatch.setattr(
        "app.workflows.territory_crawl.get_effective_google_maps_key",
        lambda _db: "AIzaStubForTest1234567890abcdef",
    )
    monkeypatch.setattr(
        "app.workflows.territory_crawl.mirror_territory_crawl_state",
        lambda territory_id, payload: mirrored.append(
            {"territory_id": territory_id, **dict(payload)}
        ),
    )

    result = run_territory_crawl_workflow(
        task_id="crawl-workflow-001",
        territory_id=str(territory.id),
        correlation_id="corr-crawl-workflow-001",
    )

    assert result == {
        "status": "done",
        "task_id": "crawl-workflow-001",
        "territory": "Centro",
        "found": 0,
        "created": 0,
        "skipped": 0,
    }
    db.expire_all()
    task_run = get_task_run(db, "crawl-workflow-001")
    assert task_run is not None
    assert task_run.task_name == "task_crawl_territory"
    assert task_run.scope_key == str(territory.id)
    assert task_run.correlation_id == "corr-crawl-workflow-001"
    assert task_run.status == "succeeded"
    assert task_run.current_step == "completed"
    assert task_run.progress_json["territory"] == "Centro"
    assert task_run.progress_json["current_city"] == "Cordoba"
    assert task_run.result["status"] == "done"
    assert mirrored[-1]["status"] == "done"


def test_task_crawl_territory_delegates_to_workflow(monkeypatch):
    captured: dict[str, object] = {}

    def fake_workflow(**kwargs):
        captured.update(kwargs)
        return {
            "status": "done",
            "task_id": kwargs["task_id"],
            "territory": "Centro",
            "found": 0,
            "created": 0,
            "skipped": 0,
        }

    monkeypatch.setattr("app.workers.crawl_tasks.run_territory_crawl_workflow", fake_workflow)

    result = task_crawl_territory.run(
        territory_id="territory-001",
        correlation_id="corr-crawl-wrapper-001",
        max_results_per_category=15,
        target_leads=30,
    )

    assert result["status"] == "done"
    assert captured["territory_id"] == "territory-001"
    assert captured["correlation_id"] == "corr-crawl-wrapper-001"
    assert captured["max_results_per_category"] == 15
    assert captured["target_leads"] == 30
    assert captured["queue"] == "default"
    assert captured["task_id"]
