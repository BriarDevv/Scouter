from datetime import UTC, datetime

from app.llm.roles import LLMRole
from app.models.inbound_mail import EmailThread, InboundMessage
from app.models.lead import Lead
from app.models.outreach import DraftStatus, OutreachDraft
from app.models.outreach_delivery import OutreachDelivery, OutreachDeliveryStatus


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
    monkeypatch.setattr(
        "app.services.review_service.resolve_model_for_role", lambda role: "qwen3.5:27b"
    )

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
    monkeypatch.setattr(
        "app.services.review_service.resolve_model_for_role", lambda role: "qwen3.5:27b"
    )

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


def test_review_inbound_message_endpoint_uses_reviewer_payload(client, db, monkeypatch):
    lead = Lead(
        business_name="Reviewer Reply Lead",
        industry="Retail",
        city="Rosario",
        email="owner@example.com",
    )
    db.add(lead)
    db.flush()

    draft = OutreachDraft(
        lead_id=lead.id,
        subject="Hola",
        body="Draft body",
        status=DraftStatus.SENT,
        sent_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    db.add(draft)
    db.flush()

    delivery = OutreachDelivery(
        lead_id=lead.id,
        draft_id=draft.id,
        provider="smtp",
        provider_message_id="out-msg-123",
        recipient_email=lead.email,
        subject_snapshot=draft.subject,
        status=OutreachDeliveryStatus.SENT,
        sent_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    db.add(delivery)
    db.flush()

    thread = EmailThread(
        lead_id=lead.id,
        draft_id=draft.id,
        delivery_id=delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        thread_key="thread-123",
        matched_via="message_id",
        match_confidence=1.0,
        last_message_at=datetime(2026, 3, 13, 11, 0, tzinfo=UTC),
    )
    db.add(thread)
    db.flush()

    message = InboundMessage(
        dedupe_key="imap:INBOX:reply-123",
        thread_id=thread.id,
        lead_id=lead.id,
        draft_id=draft.id,
        delivery_id=delivery.id,
        provider="imap",
        provider_mailbox="INBOX",
        provider_message_id="reply-123",
        message_id="<reply-123@example.com>",
        in_reply_to="<out-msg-123>",
        from_email="owner@example.com",
        from_name="Owner",
        to_email="sales@example.com",
        subject="Re: Hola",
        body_text="Me interesa, coordinemos una reunión.",
        body_snippet="Me interesa, coordinemos una reunión.",
        classification_label="asked_for_meeting",
        summary="Quiere coordinar una reunión.",
        next_action_suggestion="Responder con horarios.",
        should_escalate_reviewer=True,
        received_at=datetime(2026, 3, 13, 11, 0, tzinfo=UTC),
    )
    db.add(message)
    db.commit()

    monkeypatch.setattr(
        "app.services.review_service.llm_review_inbound_reply",
        lambda **kwargs: {
            "verdict": "reply_now",
            "confidence": "high",
            "reasoning": "Es una respuesta valiosa y con intención concreta.",
            "recommended_action": "Responder hoy proponiendo dos horarios.",
            "suggested_response_angle": "Centrarse en coordinar la reunión.",
            "watchouts": ["Confirmar disponibilidad"],
        },
    )
    monkeypatch.setattr(
        "app.services.review_service.resolve_model_for_role", lambda role: "qwen3.5:27b"
    )

    resp = client.post(f"/api/v1/reviews/inbound/messages/{message.id}")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["inbound_message_id"] == str(message.id)
    assert payload["lead_id"] == str(lead.id)
    assert payload["classification_label"] == "asked_for_meeting"
    assert payload["role"] == LLMRole.REVIEWER.value
    assert payload["model"] == "qwen3.5:27b"
    assert payload["verdict"] == "reply_now"


def test_review_inbound_message_async_endpoint_queues_task(client, db, monkeypatch):
    lead = Lead(
        business_name="Async Reviewer Reply Lead",
        city="Cordoba",
        email="owner@example.com",
    )
    db.add(lead)
    db.flush()

    thread = EmailThread(
        lead_id=lead.id,
        provider="imap",
        provider_mailbox="INBOX",
        thread_key="thread-async-123",
        matched_via="unmatched",
    )
    db.add(thread)
    db.flush()

    message = InboundMessage(
        dedupe_key="imap:INBOX:reply-async-123",
        thread_id=thread.id,
        lead_id=lead.id,
        provider="imap",
        provider_mailbox="INBOX",
        provider_message_id="reply-async-123",
        message_id="<reply-async-123@example.com>",
        from_email="owner@example.com",
        to_email="sales@example.com",
        subject="Consulta",
        body_text="¿Me pasan más info?",
        body_snippet="¿Me pasan más info?",
        received_at=datetime(2026, 3, 13, 12, 0, tzinfo=UTC),
    )
    db.add(message)
    db.commit()

    class DummyTask:
        id = "review-inbound-task-789"

    monkeypatch.setattr(
        "app.api.v1.reviews.task_review_inbound_message.delay", lambda message_id: DummyTask()
    )

    resp = client.post(f"/api/v1/reviews/inbound/messages/{message.id}/async")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["task_id"] == "review-inbound-task-789"
    assert payload["queue"] == "reviewer"
    assert payload["lead_id"] == str(lead.id)
    assert payload["current_step"] == "inbound_reply_review"
