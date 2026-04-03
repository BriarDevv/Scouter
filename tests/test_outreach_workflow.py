import uuid

from app.models.lead import Lead
from app.models.outreach import DraftStatus, OutreachDraft, OutreachLog
from app.workflows.outreach_draft_generation import (
    run_outreach_draft_generation_workflow,
    should_generate_outreach_email_draft,
)


def test_run_outreach_draft_generation_workflow_persists_degraded_ai_metadata(
    db, monkeypatch
):
    lead = Lead(
        business_name="Fallback Draft Lead",
        city="Cordoba",
        email="hello@example.com",
        llm_quality="high",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    def broken_call(system_prompt, user_prompt, role):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr("app.llm.client._chat_completion", broken_call)

    result = run_outreach_draft_generation_workflow(db, lead.id)

    assert result.status == "ok"
    assert result.ai_fallback_used is True
    assert result.ai_degraded is True

    draft = db.get(OutreachDraft, uuid.UUID(result.draft_id))
    assert draft is not None
    assert draft.status == DraftStatus.PENDING_REVIEW
    assert draft.generation_metadata_json is not None
    assert draft.generation_metadata_json["fallback_used"] is True
    assert draft.generation_metadata_json["degraded"] is True
    assert draft.generation_metadata_json["function_name"] == "generate_outreach_draft"

    log = db.query(OutreachLog).filter_by(draft_id=draft.id).first()
    assert log is not None
    assert log.detail == "ai_degraded=true; ai_fallback_used=true"


def test_should_generate_outreach_email_draft_matches_quality_gate(db):
    lead = Lead(business_name="Gate Lead", city="Rosario", email="ops@example.com")
    db.add(lead)
    db.commit()

    assert should_generate_outreach_email_draft(lead) is False

    lead.llm_quality = "high"
    db.commit()
    assert should_generate_outreach_email_draft(lead) is True
