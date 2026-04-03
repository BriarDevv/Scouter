from types import SimpleNamespace

from app.models.commercial_brief import BriefStatus
from app.models.lead import Lead
from app.models.task_tracking import TaskRun
from app.services.pipeline.task_tracking_service import get_task_run, tracked_task_step
from app.workers.brief_tasks import task_generate_brief


def test_tracked_task_step_marks_running_and_succeeds(db):
    lead = Lead(business_name="Harness Lead", city="Cordoba")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    with tracked_task_step(
        db,
        task_id="tracked-step-001",
        task_name="task_test_harness",
        queue="default",
        lead_id=lead.id,
        current_step="demo_step",
    ) as tracker:
        tracker.succeed({"status": "ok"})

    db.expire_all()
    task_run = get_task_run(db, "tracked-step-001")
    assert task_run is not None
    assert task_run.status == "succeeded"
    assert task_run.current_step == "demo_step"
    assert task_run.result == {"status": "ok"}


def test_task_generate_brief_uses_tracked_harness(db, monkeypatch):
    lead = Lead(business_name="Brief Harness Lead", city="Rosario")
    db.add(lead)
    db.commit()
    db.refresh(lead)

    fake_brief = SimpleNamespace(status=BriefStatus.GENERATED, opportunity_score=82)

    monkeypatch.setattr(
        "app.workers.brief_tasks.task_review_brief.delay",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.research.brief_service.generate_brief",
        lambda db_session, lead_id: fake_brief,
    )

    result = task_generate_brief.run(str(lead.id))

    assert result["status"] == "ok"

    task_runs = db.query(TaskRun).filter_by(task_name="task_generate_brief").all()
    assert len(task_runs) == 1
    task_run = task_runs[0]
    assert task_run.status == "succeeded"
    assert task_run.current_step == "brief_generation"
    assert task_run.result["opportunity_score"] == 82
