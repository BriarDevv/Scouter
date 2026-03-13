from app.llm.roles import LLMRole
from app.models.lead import Lead
from app.models.outreach import DraftStatus, OutreachDraft


def test_review_lead_endpoint_uses_reviewer_payload(client, db, monkeypatch):
    lead = Lead(
        business_name="Reviewer Lead",
        industry="Legal",
        city="Cordoba",
        score=71,
        llm_summary="Good local presence",
        llm_suggested_angle="Redesign",
    )
    db.add(lead)
    db.commit()

    monkeypatch.setattr(
        "app.services.review_service.llm_review_lead",
        lambda **kwargs: {
            "verdict": "priority",
            "confidence": "high",
            "reasoning": "Strong fit for premium web work.",
            "recommended_action": "Run full outreach this week.",
            "watchouts": ["Confirm owner availability"],
        },
    )
    monkeypatch.setattr("app.services.review_service.resolve_model_for_role", lambda role: "qwen3.5:27b")

    resp = client.post(f"/api/v1/reviews/leads/{lead.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["lead_id"] == str(lead.id)
    assert payload["role"] == LLMRole.REVIEWER.value
    assert payload["model"] == "qwen3.5:27b"
    assert payload["verdict"] == "priority"


def test_review_draft_endpoint_uses_reviewer_payload(client, db, monkeypatch):
    lead = Lead(
        business_name="Reviewer Draft Lead",
        industry="Retail",
        city="Rosario",
        llm_summary="Needs a clearer website CTA",
        llm_suggested_angle="Conversion-focused redesign",
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Draft subject",
        body="Draft body",
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)
    db.commit()

    monkeypatch.setattr(
        "app.services.review_service.llm_review_outreach_draft",
        lambda **kwargs: {
            "verdict": "revise",
            "confidence": "medium",
            "reasoning": "The value proposition is solid but too generic.",
            "strengths": ["Warm tone"],
            "concerns": ["Needs stronger specificity"],
            "suggested_changes": ["Mention the website CTA issue"],
            "revised_subject": "Una mejora puntual para tu web",
            "revised_body": "Hola, vi una mejora concreta para tu sitio...",
        },
    )
    monkeypatch.setattr("app.services.review_service.resolve_model_for_role", lambda role: "qwen3.5:27b")

    resp = client.post(f"/api/v1/reviews/drafts/{draft.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["draft_id"] == str(draft.id)
    assert payload["lead_id"] == str(lead.id)
    assert payload["role"] == LLMRole.REVIEWER.value
    assert payload["model"] == "qwen3.5:27b"
    assert payload["verdict"] == "revise"


def test_review_lead_async_endpoint_queues_task(client, db, monkeypatch):
    lead = Lead(
        business_name="Async Reviewer Lead",
        city="Cordoba",
    )
    db.add(lead)
    db.commit()

    class DummyTask:
        id = "review-lead-task-123"

    monkeypatch.setattr("app.api.v1.reviews.task_review_lead.delay", lambda lead_id: DummyTask())

    resp = client.post(f"/api/v1/reviews/leads/{lead.id}/async")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["task_id"] == "review-lead-task-123"
    assert payload["queue"] == "reviewer"
    assert payload["lead_id"] == str(lead.id)
    assert payload["current_step"] == "lead_review"


def test_review_draft_async_endpoint_queues_task(client, db, monkeypatch):
    lead = Lead(
        business_name="Async Reviewer Draft Lead",
        city="Rosario",
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Draft subject",
        body="Draft body",
        status=DraftStatus.PENDING_REVIEW,
    )
    db.add(draft)
    db.commit()

    class DummyTask:
        id = "review-draft-task-456"

    monkeypatch.setattr("app.api.v1.reviews.task_review_draft.delay", lambda draft_id: DummyTask())

    resp = client.post(f"/api/v1/reviews/drafts/{draft.id}/async")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["task_id"] == "review-draft-task-456"
    assert payload["queue"] == "reviewer"
    assert payload["lead_id"] == str(lead.id)
    assert payload["current_step"] == "draft_review"
