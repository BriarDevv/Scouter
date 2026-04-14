"""Regression tests for GET /api/v1/leads/{lead_id}/timeline.

Exercises the wire-level schema, 404 path, empty-state response,
descending ordering, pagination correctness, and the 500-entry max limit.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.lead import Lead, LeadStatus
from app.services.leads.event_service import emit_lead_event


def _make_lead(db) -> Lead:
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Timeline Biz",
        city="BA",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def _seed_events(db, lead_id: uuid.UUID, n: int) -> list[datetime]:
    """Create n events with deterministic timestamps and return them."""
    base = datetime.now(UTC)
    timestamps = []
    events = []
    for i in range(n):
        ev = emit_lead_event(
            db,
            lead_id=lead_id,
            event_type=f"event_{i}",
            new_status=None,
        )
        events.append(ev)
        timestamps.append(base - timedelta(seconds=(n - i)))  # older first
    db.commit()
    # Back-date explicitly for deterministic ordering.
    for ev, ts in zip(events, timestamps, strict=True):
        ev.created_at = ts
    db.commit()
    return timestamps


def test_timeline_returns_404_for_unknown_lead(client):
    resp = client.get(f"/api/v1/leads/{uuid.uuid4()}/timeline")
    assert resp.status_code == 404


def test_timeline_empty_when_lead_has_no_events(db, client):
    lead = _make_lead(db)
    resp = client.get(f"/api/v1/leads/{lead.id}/timeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_timeline_orders_events_desc_by_created_at(db, client):
    lead = _make_lead(db)
    _seed_events(db, lead.id, n=3)
    resp = client.get(f"/api/v1/leads/{lead.id}/timeline")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [i["event_type"] for i in items] == ["event_2", "event_1", "event_0"]


def test_timeline_pagination_limit_offset(db, client):
    lead = _make_lead(db)
    _seed_events(db, lead.id, n=5)
    # Page 1: limit=2
    page1 = client.get(f"/api/v1/leads/{lead.id}/timeline?limit=2&offset=0").json()
    assert page1["total"] == 5
    assert page1["limit"] == 2
    assert page1["offset"] == 0
    assert [i["event_type"] for i in page1["items"]] == ["event_4", "event_3"]
    # Page 2: limit=2, offset=2
    page2 = client.get(f"/api/v1/leads/{lead.id}/timeline?limit=2&offset=2").json()
    assert [i["event_type"] for i in page2["items"]] == ["event_2", "event_1"]


def test_timeline_rejects_limit_above_500(db, client):
    lead = _make_lead(db)
    resp = client.get(f"/api/v1/leads/{lead.id}/timeline?limit=501")
    # FastAPI Query(..., le=500) rejects with 422
    assert resp.status_code == 422


def test_timeline_accepts_limit_at_boundary_500(db, client):
    lead = _make_lead(db)
    resp = client.get(f"/api/v1/leads/{lead.id}/timeline?limit=500")
    assert resp.status_code == 200
    assert resp.json()["limit"] == 500
