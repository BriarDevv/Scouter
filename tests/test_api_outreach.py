from datetime import UTC, datetime, timedelta

from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, OutreachDraft


def test_patch_lead_status_creates_activity_log(client):
    created = client.post("/api/v1/leads", json={"business_name": "Status Test", "city": "Cordoba"})
    lead_id = created.json()["id"]

    resp = client.patch(f"/api/v1/leads/{lead_id}/status", json={"status": "contacted"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "contacted"

    logs = client.get(f"/api/v1/outreach/logs?lead_id={lead_id}")
    assert logs.status_code == 200
    payload = logs.json()
    assert len(payload) == 1
    assert payload[0]["action"] == "sent"


def test_patch_draft_updates_status_and_lead(db, client):
    lead = Lead(
        business_name="Draft Test",
        city="Rosario",
        status=LeadStatus.DRAFT_READY,
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Initial subject",
        body="Initial body",
        status=DraftStatus.PENDING_REVIEW,
        generated_at=datetime.now(UTC) - timedelta(days=1),
    )
    db.add(draft)
    db.commit()

    resp = client.patch(
        f"/api/v1/outreach/drafts/{draft.id}",
        json={"status": "approved", "feedback": "Looks good"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "approved"
    assert payload["reviewed_at"] is not None

    refreshed_lead = db.get(Lead, lead.id)
    assert refreshed_lead is not None
    assert refreshed_lead.status == LeadStatus.APPROVED

    logs = client.get(f"/api/v1/outreach/logs?draft_id={draft.id}")
    assert logs.status_code == 200
    log_payload = logs.json()
    assert len(log_payload) == 1
    assert log_payload[0]["action"] == "approved"
    assert log_payload[0]["detail"] == "Looks good"
