from app.llm.client import (
    _ChatCompletion,
    evaluate_lead_quality_structured,
    generate_commercial_brief_structured,
    review_commercial_brief_structured,
)
from app.llm.invocation_metadata import clear_last_invocation, pop_last_invocation
from app.llm.types import LLMInvocationStatus
from app.models.lead import Lead
from app.models.llm_invocation import LLMInvocation
from app.services.research.brief_service import generate_brief


def test_lead_quality_structured_persists_prompt_metadata(db, monkeypatch):
    clear_last_invocation()

    def fake_chat(system_prompt, user_prompt, role, format_schema=None):
        assert format_schema is not None
        return _ChatCompletion(
            text=(
                '{"quality":"high","reasoning":"Buen fit comercial",'
                '"suggested_angle":"Reforzar conversiones"}'
            ),
            model="qwen3.5:9b",
            latency_ms=123,
        )

    monkeypatch.setattr("app.llm.client._chat_completion", fake_chat)

    result = evaluate_lead_quality_structured(
        business_name="Cafe Test",
        industry="Cafe",
        city="CABA",
        website_url="https://example.com",
        instagram_url=None,
        signals=[],
        score=84,
        target_type="lead",
        target_id="lead-123",
        tags={"workflow": "task_analyze_lead"},
    )

    assert result.status == LLMInvocationStatus.SUCCEEDED
    assert result.parse_valid is True
    assert result.prompt_id == "lead_quality.evaluate"
    assert result.prompt_version == "v2"
    assert result.parsed is not None
    assert result.parsed.quality == "high"

    metadata = pop_last_invocation()
    assert metadata is not None
    assert metadata.prompt_id == "lead_quality.evaluate"
    assert metadata.status == LLMInvocationStatus.SUCCEEDED
    assert metadata.parse_valid is True
    assert metadata.latency_ms == 123

    db.expire_all()
    row = db.query(LLMInvocation).filter_by(prompt_id="lead_quality.evaluate").one()
    assert row.function_name == "evaluate_lead_quality"
    assert row.status == LLMInvocationStatus.SUCCEEDED
    assert row.target_type == "lead"
    assert row.target_id == "lead-123"
    assert row.tags_json == {"workflow": "task_analyze_lead"}


def test_lead_quality_structured_fallback_marks_failure_explicitly(db, monkeypatch):
    clear_last_invocation()

    def broken_chat(system_prompt, user_prompt, role, format_schema=None):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr("app.llm.client._chat_completion", broken_chat)

    result = evaluate_lead_quality_structured(
        business_name="Cafe Test",
        industry="Cafe",
        city="CABA",
        website_url="https://example.com",
        instagram_url=None,
        signals=[],
        score=40,
        target_type="lead",
        target_id="lead-456",
    )

    assert result.status == LLMInvocationStatus.FALLBACK
    assert result.fallback_used is True
    assert result.degraded is True
    assert result.parse_valid is False
    assert result.parsed is not None
    assert result.parsed.quality == "unknown"

    metadata = pop_last_invocation()
    assert metadata is not None
    assert metadata.status == LLMInvocationStatus.FALLBACK
    assert metadata.fallback_used is True
    assert metadata.error == "ollama unavailable"

    db.expire_all()
    row = db.query(LLMInvocation).filter_by(target_id="lead-456").one()
    assert row.status == LLMInvocationStatus.FALLBACK
    assert row.parse_valid is False
    assert row.error == "ollama unavailable"


def test_commercial_brief_structured_marks_heuristic_parse_as_degraded(db, monkeypatch):
    clear_last_invocation()

    def fake_chat(system_prompt, user_prompt, role, format_schema=None):
        assert format_schema is not None
        return _ChatCompletion(
            text=(
                'Acá va el brief:\n{"opportunity_score": 91, '
                '"estimated_scope": "automation", '
                '"recommended_contact_method": "email", '
                '"should_call": "maybe", '
                '"call_reason": "Conviene validar primero por email.", '
                '"why_this_lead_matters": "Tiene una necesidad digital clara.", '
                '"main_business_signals": ["vende servicios premium"], '
                '"main_digital_gaps": ["no tiene automatización"], '
                '"recommended_angle": "Mostrar mejoras de procesos", '
                '"demo_recommended": true}\nGracias.'
            ),
            model="qwen3.5:9b",
            latency_ms=88,
        )

    monkeypatch.setattr("app.llm.client._chat_completion", fake_chat)

    result = generate_commercial_brief_structured(
        business_name="Studio Test",
        industry="Consultoria",
        city="Rosario",
        website_url="https://example.com",
        instagram_url=None,
        score=91,
        llm_summary="Empresa con buena tracción.",
        signals=["weak_seo"],
        research_data={"website_confidence": "high"},
        pricing_matrix={"automation": {"min": 800, "max": 3000}},
        target_type="commercial_brief",
        target_id="brief-123",
    )

    assert result.status == LLMInvocationStatus.DEGRADED
    assert result.degraded is True
    assert result.fallback_used is False
    assert result.parse_valid is True
    assert result.parsed is not None
    assert result.parsed.estimated_scope == "automation"

    db.expire_all()
    row = db.query(LLMInvocation).filter_by(target_id="brief-123").one()
    assert row.prompt_id == "commercial_brief.generate"
    assert row.status == LLMInvocationStatus.DEGRADED
    assert row.parse_valid is True


def test_generate_brief_and_review_use_typed_invocation_seam(db, monkeypatch):
    lead = Lead(
        business_name="Typed Brief Lead",
        city="Cordoba",
        industry="Retail",
        website_url="https://typed.example.com",
        score=73,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    responses = iter(
        [
            _ChatCompletion(
                text=(
                    '{"opportunity_score": 73,'
                    '"estimated_scope":"redesign",'
                    '"recommended_contact_method":"email",'
                    '"should_call":"no",'
                    '"call_reason":"Primero conviene abrir conversación.",'
                    '"why_this_lead_matters":"Tiene presencia digital mejorable.",'
                    '"main_business_signals":["marca activa"],'
                    '"main_digital_gaps":["sitio desactualizado"],'
                    '"recommended_angle":"Modernizar conversión y confianza",'
                    '"demo_recommended":false}'
                ),
                model="qwen3.5:9b",
                latency_ms=75,
            ),
            _ChatCompletion(
                text=(
                    '{"approved": true, "feedback": "Listo para avanzar.", '
                    '"suggested_changes": null}'
                ),
                model="qwen3.5:27b",
                latency_ms=110,
            ),
        ]
    )

    def fake_chat(system_prompt, user_prompt, role, format_schema=None):
        return next(responses)

    monkeypatch.setattr("app.llm.client._chat_completion", fake_chat)

    brief = generate_brief(db, lead.id)

    assert brief is not None
    assert brief.generator_model == "qwen3.5:9b"
    assert brief.is_fallback is False

    review_result = review_commercial_brief_structured(
        opportunity_score=brief.opportunity_score,
        budget_tier=brief.budget_tier.value if brief.budget_tier else None,
        estimated_scope=brief.estimated_scope.value if brief.estimated_scope else None,
        recommended_contact_method=(
            brief.recommended_contact_method.value if brief.recommended_contact_method else None
        ),
        should_call=brief.should_call.value if brief.should_call else None,
        call_reason=brief.call_reason,
        why_this_lead_matters=brief.why_this_lead_matters,
        main_business_signals=brief.main_business_signals,
        main_digital_gaps=brief.main_digital_gaps,
        recommended_angle=brief.recommended_angle,
        demo_recommended=brief.demo_recommended,
        target_type="commercial_brief",
        target_id=str(brief.id),
        tags={"lead_id": str(lead.id)},
    )

    assert review_result.status == LLMInvocationStatus.SUCCEEDED
    assert review_result.parsed is not None
    assert review_result.parsed.approved is True

    db.expire_all()
    invocation_rows = (
        db.query(LLMInvocation).filter(LLMInvocation.target_type == "commercial_brief").all()
    )
    prompt_ids = {row.prompt_id for row in invocation_rows}
    assert "commercial_brief.generate" in prompt_ids
    assert "commercial_brief.review" in prompt_ids
