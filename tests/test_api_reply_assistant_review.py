from app.llm.roles import LLMRole
from app.models.reply_assistant import (
    ReplyAssistantDraft,
    ReplyAssistantReview,
    ReplyAssistantReviewStatus,
)
from app.services.inbox.reply_draft_review_service import (
    get_reply_assistant_review_for_message,
    review_reply_assistant_draft_with_reviewer,
)
from tests.test_api_reply_assistant import _seed_inbound_reply


def _generate_reply_assistant_draft(client, message_id, monkeypatch):
    monkeypatch.setattr(
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: {
            "subject": "Re: Seguimiento sitio web",
            "body": "Hola, gracias por escribir. Te comparto una propuesta breve.",
            "summary": "Responde al pedido de propuesta con un siguiente paso claro.",
            "suggested_tone": "consultative",
            "should_escalate_reviewer": False,
        },
    )
    response = client.post(f"/api/v1/replies/{message_id}/draft-response")
    assert response.status_code == 200
    return response.json()


def test_request_reply_assistant_review_creates_pending_review(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)
    _generate_reply_assistant_draft(client, message.id, monkeypatch)

    class DummyTask:
        id = "reply-draft-review-task-001"

    monkeypatch.setattr(
        "app.api.v1.replies.task_review_reply_assistant_draft.delay",
        lambda message_id: DummyTask(),
    )

    response = client.post(f"/api/v1/replies/{message.id}/draft-response/review")
    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "reply-draft-review-task-001"
    assert payload["queue"] == "reviewer"
    assert payload["current_step"] == "reply_draft_review"

    review = get_reply_assistant_review_for_message(db, message.id)
    assert review is not None
    assert review.status == ReplyAssistantReviewStatus.PENDING
    assert review.task_id == "reply-draft-review-task-001"


def test_get_reply_assistant_review_returns_404_when_absent(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)
    _generate_reply_assistant_draft(client, message.id, monkeypatch)

    response = client.get(f"/api/v1/replies/{message.id}/draft-response/review")
    assert response.status_code == 404
    assert "Reply assistant draft review not found" in response.json()["detail"]


def test_review_reply_assistant_draft_with_reviewer_persists_result(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)
    draft_payload = _generate_reply_assistant_draft(client, message.id, monkeypatch)

    monkeypatch.setattr(
        "app.services.inbox.reply_draft_review_service.llm_review_reply_assistant_draft",
        lambda **kwargs: {
            "summary": "El draft está bastante bien y solo necesita un cierre más concreto.",
            "feedback": "Conviene hacer más explícita la propuesta y cerrar con CTA puntual.",
            "suggested_edits": [
                "Agregar una línea con alcance resumido.",
                "Cerrar proponiendo una franja horaria para conversar.",
            ],
            "recommended_action": "edit_before_sending",
            "should_use_as_is": False,
            "should_edit": True,
            "should_escalate": False,
        },
    )
    monkeypatch.setattr(
        "app.services.inbox.reply_draft_review_service.resolve_model_for_role",
        lambda role: "qwen3.5:27b",
    )

    payload = review_reply_assistant_draft_with_reviewer(db, message.id)
    assert payload is not None
    assert str(payload["reply_assistant_draft_id"]) == draft_payload["id"]
    assert payload["role"] == LLMRole.REVIEWER
    assert payload["model"] == "qwen3.5:27b"
    assert payload["recommended_action"] == "edit_before_sending"

    review = get_reply_assistant_review_for_message(db, message.id)
    assert review is not None
    assert review.status == ReplyAssistantReviewStatus.REVIEWED
    assert review.feedback == "Conviene hacer más explícita la propuesta y cerrar con CTA puntual."
    assert review.suggested_edits == [
        "Agregar una línea con alcance resumido.",
        "Cerrar proponiendo una franja horaria para conversar.",
    ]


def test_regenerating_reply_assistant_draft_discards_previous_review(client, db, monkeypatch):
    _, _, _, _, message = _seed_inbound_reply(db)

    generator_responses = iter(
        [
            {
                "subject": "Re: Seguimiento sitio web",
                "body": "Primera versión de respuesta.",
                "summary": "Primer draft generado.",
                "suggested_tone": "brief",
                "should_escalate_reviewer": False,
            },
            {
                "subject": "Re: Seguimiento sitio web",
                "body": "Segunda versión con mejor CTA.",
                "summary": "Draft regenerado.",
                "suggested_tone": "consultative",
                "should_escalate_reviewer": True,
            },
        ]
    )
    monkeypatch.setattr(
        "app.services.inbox.reply_response_service.llm_generate_reply_assistant_draft",
        lambda **kwargs: next(generator_responses),
    )

    first = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert first.status_code == 200

    draft = db.query(ReplyAssistantDraft).one()
    review = ReplyAssistantReview(
        reply_assistant_draft_id=draft.id,
        inbound_message_id=message.id,
        thread_id=message.thread_id,
        lead_id=message.lead_id,
        status=ReplyAssistantReviewStatus.REVIEWED,
        summary="Está usable.",
        should_use_as_is=True,
        should_edit=False,
        should_escalate=False,
        reviewer_role="reviewer",
        reviewer_model="qwen3.5:27b",
    )
    db.add(review)
    db.commit()

    second = client.post(f"/api/v1/replies/{message.id}/draft-response")
    assert second.status_code == 200
    payload = second.json()
    assert payload["review"] is None
    assert db.query(ReplyAssistantReview).count() == 0
