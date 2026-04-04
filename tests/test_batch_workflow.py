from app.models.lead import Lead
from app.models.task_tracking import TaskRun
from app.services.pipeline.operational_task_service import BATCH_PIPELINE_SCOPE_KEY
from app.services.pipeline.task_tracking_service import get_task_run
from app.workers.pipeline_tasks import task_generate_draft
from app.workers.tasks import task_batch_pipeline
from app.workflows.batch_pipeline import run_batch_pipeline_workflow


def test_run_batch_pipeline_workflow_completes_without_pending_leads(db, monkeypatch):
    task_run = TaskRun(
        task_id="batch-workflow-001",
        task_name="task_batch_pipeline",
        queue="default",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        status="running",
        current_step="batch_dispatch",
    )
    db.add(task_run)
    db.commit()

    mirrored: list[dict] = []

    monkeypatch.setattr(
        "app.workflows.batch_pipeline.should_stop_operational_task",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        "app.workflows.batch_pipeline.mirror_batch_pipeline_state",
        lambda payload: mirrored.append(dict(payload)),
    )

    result = run_batch_pipeline_workflow(
        task_id="batch-workflow-001",
        status_filter="new",
        correlation_id="corr-batch-workflow-001",
        crawl_territory_workflow=lambda **kwargs: None,
    )

    assert result == {
        "status": "done",
        "task_id": "batch-workflow-001",
        "total": 0,
        "errors": 0,
    }
    db.expire_all()
    refreshed = get_task_run(db, "batch-workflow-001")
    assert refreshed is not None
    assert refreshed.status == "succeeded"
    assert refreshed.current_step == "completed"
    assert refreshed.result["status"] == "done"
    assert refreshed.progress_json["processed"] == 0
    assert mirrored[-1]["status"] == "done"


def test_task_batch_pipeline_delegates_to_workflow(db, monkeypatch):
    captured: dict[str, object] = {}

    def fake_workflow(**kwargs):
        captured.update(kwargs)
        return {
            "status": "done",
            "task_id": kwargs["task_id"],
            "total": 0,
            "errors": 0,
        }

    monkeypatch.setattr("app.workers.batch_tasks.run_batch_pipeline_workflow", fake_workflow)

    result = task_batch_pipeline.run(
        status_filter="new",
        correlation_id="corr-batch-wrapper-001",
    )

    assert result["status"] == "done"
    assert captured["status_filter"] == "new"
    assert captured["correlation_id"] == "corr-batch-wrapper-001"

    task_run = get_task_run(db, str(captured["task_id"]))
    assert task_run is not None
    assert task_run.task_name == "task_batch_pipeline"
    assert task_run.scope_key == BATCH_PIPELINE_SCOPE_KEY
    assert task_run.status == "running"


def test_run_batch_pipeline_uses_crawl_workflow_seam_for_auto_crawl(db, monkeypatch):
    task_run = TaskRun(
        task_id="batch-workflow-002",
        task_name="task_batch_pipeline",
        queue="default",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        status="running",
        current_step="batch_dispatch",
    )
    db.add(task_run)

    from app.models.territory import Territory

    territory = Territory(name="Centro", cities=["Cordoba"])
    db.add(territory)
    db.commit()
    db.refresh(territory)

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.workflows.batch_pipeline.should_stop_operational_task",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        "app.workflows.batch_pipeline.mirror_batch_pipeline_state",
        lambda payload: None,
    )

    def fake_crawl_workflow(**kwargs):
        captured.update(kwargs)
        return {"status": "done", "task_id": kwargs["task_id"], "created": 0}

    result = run_batch_pipeline_workflow(
        task_id="batch-workflow-002",
        status_filter="new",
        correlation_id="corr-batch-workflow-002",
        crawl_territory_workflow=fake_crawl_workflow,
    )

    assert result["status"] == "done"
    assert captured["territory_id"] == str(territory.id)
    assert captured["correlation_id"] == "corr-batch-workflow-002"
    assert captured["task_id"] != "batch-workflow-002"


def test_run_batch_pipeline_uses_shared_lead_pipeline_steps(db, monkeypatch):
    task_run = TaskRun(
        task_id="batch-workflow-003",
        task_name="task_batch_pipeline",
        queue="default",
        scope_key=BATCH_PIPELINE_SCOPE_KEY,
        status="running",
        current_step="batch_dispatch",
    )
    lead = Lead(
        business_name="Shared Step Lead",
        city="Mendoza",
        status="new",
        email="shared@example.com",
    )
    db.add(task_run)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "app.workflows.batch_pipeline.should_stop_operational_task",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        "app.workflows.batch_pipeline.mirror_batch_pipeline_state",
        lambda payload: None,
    )

    def fake_enrich(db_session, lead_id):
        calls.append(("enrich", str(lead_id)))
        return db_session.get(Lead, lead_id)

    def fake_score(db_session, lead_id):
        calls.append(("score", str(lead_id)))
        return db_session.get(Lead, lead_id)

    def fake_analysis(db_session, lead_obj, *, source_tag, role=None):
        calls.append(("analysis", source_tag))
        lead_obj.llm_quality = "medium"
        lead_obj.llm_summary = "summary"
        return type(
            "AnalysisResult",
            (),
            {
                "summary": "summary",
                "quality": "medium",
                "reasoning": "ok",
                "suggested_angle": "angle",
            },
        )()

    def fake_draft(db_session, lead_id, *, apply_automation=True):
        calls.append(("draft", str(lead_id)))
        db_session.get(Lead, lead_id).status = "processed"
        db_session.commit()
        return type(
            "DraftResult",
            (),
            {
                "status": "skipped",
                "reason": "quality=medium",
                "to_payload": lambda self: {
                    "status": "skipped",
                    "lead_id": str(lead_id),
                    "reason": "quality=medium",
                },
            },
        )()

    monkeypatch.setattr("app.workflows.batch_pipeline.enrich_lead", fake_enrich)
    monkeypatch.setattr("app.workflows.batch_pipeline.score_lead", fake_score)
    monkeypatch.setattr("app.workflows.batch_pipeline.run_lead_analysis_step", fake_analysis)
    monkeypatch.setattr("app.workflows.batch_pipeline.run_draft_generation_step", fake_draft)

    result = run_batch_pipeline_workflow(
        task_id="batch-workflow-003",
        status_filter="new",
        correlation_id="corr-batch-workflow-003",
        crawl_territory_workflow=lambda **kwargs: None,
    )

    assert result["status"] == "done"
    assert calls == [
        ("enrich", str(lead.id)),
        ("score", str(lead.id)),
        ("analysis", "batch_pipeline"),
        ("draft", str(lead.id)),
    ]


def test_task_generate_draft_uses_shared_draft_generation_step(db, monkeypatch):
    lead = Lead(
        business_name="Draft Step Lead",
        city="Rosario",
        status="new",
        email="draft@example.com",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    captured: dict[str, object] = {}

    def fake_run_draft_generation_step(db_session, lead_id, *, apply_automation=True, pipeline_context_text=""):
        captured["lead_id"] = str(lead_id)
        captured["apply_automation"] = apply_automation
        return type(
            "DraftResult",
            (),
            {
                "status": "ok",
                "reason": None,
                "draft_id": None,
                "to_payload": lambda self: {"status": "ok", "lead_id": str(lead_id)},
            },
        )()

    monkeypatch.setattr(
        "app.workers.pipeline_tasks.run_draft_generation_step",
        fake_run_draft_generation_step,
    )

    result = task_generate_draft.run(str(lead.id))

    assert result["status"] == "ok"
    assert captured == {"lead_id": str(lead.id), "apply_automation": True}
