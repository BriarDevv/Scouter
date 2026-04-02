"""Tests for commercial brief model and service."""

import uuid

from app.models.commercial_brief import (
    BriefStatus,
    BudgetTier,
    CommercialBrief,
)
from app.models.lead import Lead, LeadStatus


def test_commercial_brief_model(db):
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Test",
        city="CABA",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    brief = CommercialBrief(
        lead_id=lead.id,
        status=BriefStatus.GENERATED,
        opportunity_score=75.0,
        budget_tier=BudgetTier.MEDIUM,
        estimated_budget_min=500,
        estimated_budget_max=1200,
    )
    db.add(brief)
    db.commit()
    assert brief.id is not None
    assert brief.opportunity_score == 75.0
    assert brief.budget_tier == BudgetTier.MEDIUM


def test_brief_api_404_when_no_brief(client, db):
    lead = Lead(
        id=uuid.uuid4(),
        business_name="Test",
        city="CABA",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    resp = client.get(f"/api/v1/briefs/leads/{lead.id}")
    assert resp.status_code == 404


def test_list_briefs_empty(client, db):
    resp = client.get("/api/v1/briefs/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_brief_service_pricing_matrix(db):
    from app.services.brief_service import (
        DEFAULT_PRICING_MATRIX,
        get_pricing_matrix,
    )

    matrix = get_pricing_matrix(db)
    assert matrix == DEFAULT_PRICING_MATRIX


def test_infer_budget_tier():
    from app.services.brief_service import _infer_budget_tier

    assert _infer_budget_tier(500) == BudgetTier.LOW
    assert _infer_budget_tier(1000) == BudgetTier.MEDIUM
    assert _infer_budget_tier(2000) == BudgetTier.HIGH
    assert _infer_budget_tier(5000) == BudgetTier.PREMIUM
    assert _infer_budget_tier(None) is None
