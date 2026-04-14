"""Regression tests for the LeadEvent immutable event store.

Closes docs/roadmaps/post-hardening-plan.md Item 3. Verifies:

- emit_lead_event inserts a row with the expected shape
- update_lead_status hook emits exactly one event on a real transition
  and zero events on a no-op
- mark_task_succeeded emits a pipeline_step_* event when task_run is
  bound to a lead, and none otherwise
- CASCADE removes events when the parent lead is deleted
- Timeline query is ordered by created_at desc
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.inbound_mail import InboundMessage  # noqa: F401 — ensures registration
from app.models.lead import Lead, LeadStatus
from app.models.lead_event import LeadEvent
from app.models.task_tracking import TaskRun
from app.services.leads.event_service import emit_lead_event
from app.services.leads.lead_service import update_lead_status


def _make_lead(db) -> Lead:
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Event Test Biz",
        city="BA",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def test_emit_lead_event_inserts_row(db):
    lead = _make_lead(db)
    event = emit_lead_event(
        db,
        lead_id=lead.id,
        event_type="custom",
        new_status="enriched",
        payload={"k": "v"},
        actor="test",
    )
    db.commit()
    assert event.id is not None
    fresh = db.get(LeadEvent, event.id)
    assert fresh.lead_id == lead.id
    assert fresh.event_type == "custom"
    assert fresh.new_status == "enriched"
    assert fresh.payload_json == {"k": "v"}
    assert fresh.actor == "test"
    assert fresh.created_at is not None


def test_emit_lead_event_without_payload_works(db):
    lead = _make_lead(db)
    event = emit_lead_event(
        db,
        lead_id=lead.id,
        event_type="minimal",
    )
    db.commit()
    fresh = db.get(LeadEvent, event.id)
    assert fresh.payload_json is None
    assert fresh.old_status is None
    assert fresh.new_status is None
    assert fresh.actor == "system"


def test_update_lead_status_emits_event_on_real_transition(db):
    lead = _make_lead(db)
    update_lead_status(db, lead.id, LeadStatus.CONTACTED)
    db.commit()

    events = (
        db.query(LeadEvent)
        .filter(LeadEvent.lead_id == lead.id, LeadEvent.event_type == "status_changed")
        .all()
    )
    assert len(events) == 1
    assert events[0].old_status == "new"
    assert events[0].new_status == "contacted"


def test_update_lead_status_no_event_on_noop_transition(db):
    lead = _make_lead(db)
    # Setting the same status twice should emit ONE event (the first setting
    # was not triggered; the second is a no-op that should be silent).
    lead.status = LeadStatus.CONTACTED
    db.commit()
    # Now call update_lead_status with the same current status — no new event.
    update_lead_status(db, lead.id, LeadStatus.CONTACTED)
    db.commit()
    events = (
        db.query(LeadEvent)
        .filter(LeadEvent.lead_id == lead.id, LeadEvent.event_type == "status_changed")
        .all()
    )
    assert events == []


def test_mark_task_succeeded_emits_event_when_lead_bound(db):
    from app.services.pipeline.task_tracking_service import (
        mark_task_running,
        mark_task_succeeded,
    )

    lead = _make_lead(db)
    task_id = str(uuid.uuid4())
    mark_task_running(
        db,
        task_id=task_id,
        task_name="task_enrich_lead",
        queue="enrichment",
        lead_id=lead.id,
        current_step="enrichment",
    )
    db.commit()
    mark_task_succeeded(
        db,
        task_id=task_id,
        current_step="enrichment",
        result={"ok": True},
    )
    db.commit()

    events = (
        db.query(LeadEvent)
        .filter(LeadEvent.lead_id == lead.id)
        .filter(LeadEvent.event_type == "pipeline_step_enrichment")
        .all()
    )
    assert len(events) == 1
    assert events[0].actor == "pipeline"
    assert events[0].payload_json["task_id"] == task_id


def test_mark_task_succeeded_without_lead_does_not_emit_event(db):
    from app.services.pipeline.task_tracking_service import (
        mark_task_running,
        mark_task_succeeded,
    )

    task_id = str(uuid.uuid4())
    mark_task_running(
        db,
        task_id=task_id,
        task_name="task_crawl_territory",
        queue="default",
        current_step="crawl_init",
    )
    db.commit()
    mark_task_succeeded(
        db,
        task_id=task_id,
        current_step="crawl_init",
        result={"ok": True},
    )
    db.commit()

    # No events at all should be emitted for a task without lead_id.
    assert db.query(LeadEvent).count() == 0
    # Make sure the task_run exists, so we know the path ran.
    assert db.get(TaskRun, task_id) is not None


def test_cascade_deletes_events_when_lead_deleted(db):
    lead = _make_lead(db)
    emit_lead_event(db, lead_id=lead.id, event_type="before_delete")
    db.commit()
    assert db.query(LeadEvent).filter_by(lead_id=lead.id).count() == 1

    db.delete(lead)
    db.commit()
    assert db.query(LeadEvent).filter_by(lead_id=lead.id).count() == 0


def test_timeline_query_orders_desc_by_created_at(db):
    lead = _make_lead(db)
    base = datetime.now(UTC)

    e1 = emit_lead_event(db, lead_id=lead.id, event_type="first")
    e2 = emit_lead_event(db, lead_id=lead.id, event_type="second")
    e3 = emit_lead_event(db, lead_id=lead.id, event_type="third")
    db.commit()

    # Spread created_at explicitly so sort is deterministic even in fast CI.
    e1.created_at = base - timedelta(seconds=30)
    e2.created_at = base - timedelta(seconds=20)
    e3.created_at = base - timedelta(seconds=10)
    db.commit()

    timeline = (
        db.query(LeadEvent)
        .filter(LeadEvent.lead_id == lead.id)
        .order_by(LeadEvent.created_at.desc())
        .all()
    )
    assert [e.event_type for e in timeline] == ["third", "second", "first"]
