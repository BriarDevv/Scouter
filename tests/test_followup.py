"""Regression tests for the follow-up detection chain.

Closes docs/roadmaps/post-hardening-plan.md Item 2: leads that went
silent after first outreach now surface as operator notifications via
the beat-scheduled task_check_followup.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.inbound_mail import InboundMessage
from app.models.lead import Lead, LeadStatus
from app.models.notification import Notification
from app.models.settings import OperationalSettings
from app.services.outreach.followup_service import find_leads_needing_followup


def _contacted_lead(db, *, updated_at: datetime) -> Lead:
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Silent Prospect",
        city="Buenos Aires",
        status=LeadStatus.CONTACTED,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    lead.updated_at = updated_at
    db.commit()
    db.refresh(lead)
    return lead


def test_find_leads_needing_followup_includes_stale_contacted_no_inbound(db):
    lead = _contacted_lead(db, updated_at=datetime.now(UTC) - timedelta(days=5))
    result = find_leads_needing_followup(db, followup_days=3)
    assert [li.id for li in result] == [lead.id]


def test_find_leads_needing_followup_excludes_recent_contacted(db):
    _contacted_lead(db, updated_at=datetime.now(UTC) - timedelta(days=1))
    result = find_leads_needing_followup(db, followup_days=3)
    assert result == []


def test_find_leads_needing_followup_excludes_lead_with_inbound_message(db):
    lead = _contacted_lead(db, updated_at=datetime.now(UTC) - timedelta(days=10))
    inbound = InboundMessage(
        id=uuid.uuid4(),
        lead_id=lead.id,
        dedupe_key=f"test:{uuid.uuid4()}",
        provider="test",
        provider_mailbox="inbox",
        from_email="reply@example.com",
        from_name="Customer",
        subject="Re: offer",
        body_text="Interested",
        received_at=datetime.now(UTC) - timedelta(days=2),
    )
    db.add(inbound)
    db.commit()
    result = find_leads_needing_followup(db, followup_days=3)
    assert result == []


def test_find_leads_needing_followup_excludes_non_contacted_statuses(db):
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Replied Lead",
        city="BA",
        status=LeadStatus.REPLIED,
    )
    db.add(lead)
    db.commit()
    lead.updated_at = datetime.now(UTC) - timedelta(days=10)
    db.commit()
    result = find_leads_needing_followup(db, followup_days=3)
    assert result == []


def test_task_check_followup_emits_notification_per_eligible_lead(db):
    ops = db.get(OperationalSettings, 1)
    ops.followup_days = 3
    db.commit()

    lead1 = _contacted_lead(db, updated_at=datetime.now(UTC) - timedelta(days=5))
    lead2 = _contacted_lead(db, updated_at=datetime.now(UTC) - timedelta(days=10))
    # Recent lead should NOT generate a notification.
    _contacted_lead(db, updated_at=datetime.now(UTC) - timedelta(hours=1))

    from app.workers.followup_tasks import task_check_followup

    result = task_check_followup()

    assert result["status"] == "ok"
    assert result["leads_flagged"] == 2
    assert result["followup_days"] == 3

    notifs = (
        db.query(Notification)
        .filter(Notification.type == "followup_needed")
        .order_by(Notification.created_at)
        .all()
    )
    ids_seen = {n.source_id for n in notifs}
    assert {lead1.id, lead2.id}.issubset(ids_seen)
