from __future__ import annotations

from app.llm.contracts import (
    InboundReplyReviewResult,
    ReplyAssistantDraftResult,
    ReplyAssistantDraftReviewResult,
    ReplyClassificationResult,
)
from app.llm.invocations.support import get_client_module
from app.llm.prompt_registry import (
    INBOUND_REPLY_CLASSIFICATION_PROMPT,
    INBOUND_REPLY_REVIEW_PROMPT,
    REPLY_ASSISTANT_DRAFT_PROMPT,
    REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT,
)
from app.llm.roles import LLMRole
from app.llm.sanitizer import sanitize_field


def classify_inbound_reply_structured(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name) or "Unknown",
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "lead_email": sanitize_field(lead_email) or "Unknown",
        "outbound_subject": sanitize_field(outbound_subject) or "Unknown",
        "outbound_message_id": outbound_message_id or "Unknown",
        "from_email": sanitize_field(from_email) or "Unknown",
        "to_email": sanitize_field(to_email) or "Unknown",
        "subject": sanitize_field(subject) or "No subject",
        "body_text": sanitize_field(body_text) or "No body text available",
    }
    return client_module.invoke_structured(
        function_name="classify_inbound_reply",
        prompt=INBOUND_REPLY_CLASSIFICATION_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_classify_inbound_reply_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def _classify_inbound_reply_fallback() -> ReplyClassificationResult:
    return ReplyClassificationResult(
        label="needs_human_review",
        summary="Classification unavailable — LLM fallback",
        confidence=0.0,
        next_action_suggestion="Manual review required",
        should_escalate_reviewer=True,
    )


def classify_inbound_reply(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
) -> dict:
    result = classify_inbound_reply_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        lead_email=lead_email,
        outbound_subject=outbound_subject,
        outbound_message_id=outbound_message_id,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        role=role,
    )
    if result.parsed is None:
        raise get_client_module().LLMError(result.error or "Inbound reply classification failed")
    return result.parsed.model_dump()


def _review_inbound_reply_fallback() -> InboundReplyReviewResult:
    return InboundReplyReviewResult(
        verdict="consider_reply",
        confidence="low",
        reasoning="Reviewer analysis unavailable.",
        recommended_action="Review this reply manually before responding.",
        suggested_response_angle=None,
        watchouts=["Reviewer output unavailable"],
    )


def review_inbound_reply_structured(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    role: LLMRole | str = LLMRole.REVIEWER,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name) or "Unknown",
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "lead_email": sanitize_field(lead_email) or "Unknown",
        "outbound_subject": sanitize_field(outbound_subject) or "Unknown",
        "outbound_message_id": outbound_message_id or "Unknown",
        "from_email": sanitize_field(from_email) or "Unknown",
        "to_email": sanitize_field(to_email) or "Unknown",
        "subject": sanitize_field(subject) or "No subject",
        "body_text": sanitize_field(body_text) or "No body text available",
        "classification_label": classification_label or "None",
        "classification_summary": sanitize_field(classification_summary)
        or "No executor summary available",
        "next_action_suggestion": sanitize_field(next_action_suggestion)
        or "No executor suggestion available",
        "should_escalate_reviewer": "true" if should_escalate_reviewer else "false",
    }
    return client_module.invoke_structured(
        function_name="review_inbound_reply",
        prompt=INBOUND_REPLY_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_review_inbound_reply_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def review_inbound_reply(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    outbound_subject: str | None,
    outbound_message_id: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    result = review_inbound_reply_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        lead_email=lead_email,
        outbound_subject=outbound_subject,
        outbound_message_id=outbound_message_id,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        classification_label=classification_label,
        classification_summary=classification_summary,
        next_action_suggestion=next_action_suggestion,
        should_escalate_reviewer=should_escalate_reviewer,
        role=role,
    )
    if result.parsed is None:
        return _review_inbound_reply_fallback().model_dump()
    return result.parsed.model_dump()


def _reply_assistant_draft_fallback(subject: str | None) -> ReplyAssistantDraftResult:
    return ReplyAssistantDraftResult(
        subject=subject or "Re: Consulta",
        body="Gracias por tu mensaje. Quedo atento para seguir la conversación.",
        summary="Draft de respuesta generado con fallback por indisponibilidad del LLM.",
        suggested_tone="professional",
        should_escalate_reviewer=True,
    )


def generate_reply_assistant_draft_structured(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    outbound_subject: str | None,
    outbound_body: str | None,
    thread_context: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
    brand_context: dict | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    bc = brand_context or {}
    prompt_args = {
        "business_name": sanitize_field(business_name) or "Unknown",
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "lead_email": sanitize_field(lead_email) or "Unknown",
        "classification_label": classification_label or "Unknown",
        "classification_summary": sanitize_field(classification_summary)
        or "No classification summary available",
        "next_action_suggestion": sanitize_field(next_action_suggestion)
        or "No next action suggestion available",
        "should_escalate_reviewer": "true" if should_escalate_reviewer else "false",
        "outbound_subject": sanitize_field(outbound_subject) or "Unknown",
        "outbound_body": sanitize_field(outbound_body) or "Unknown",
        "thread_context": sanitize_field(thread_context) or "No previous thread context available",
        "from_email": sanitize_field(from_email) or "Unknown",
        "to_email": sanitize_field(to_email) or "Unknown",
        "subject": sanitize_field(subject) or "No subject",
        "body_text": sanitize_field(body_text) or "No body text available",
        "brand_name": bc.get("brand_name") or "No especificado",
        "signature_name": bc.get("signature_name") or "No especificado",
        "signature_role": bc.get("signature_role") or "No especificado",
        "signature_company": bc.get("signature_company") or "No especificado",
        "brand_website_url": bc.get("website_url") or "No proporcionado — NO inventar URLs",
        "signature_cta": bc.get("signature_cta") or "No especificado",
        "default_reply_tone": bc.get("default_reply_tone") or "profesional",
        "default_closing_line": bc.get("default_closing_line") or "No especificado",
        "sender_is_solo": bc.get("signature_is_solo", False),
    }
    return client_module.invoke_structured(
        function_name="generate_reply_assistant_draft",
        prompt=REPLY_ASSISTANT_DRAFT_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=lambda: _reply_assistant_draft_fallback(subject),
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def generate_reply_assistant_draft(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    should_escalate_reviewer: bool,
    outbound_subject: str | None,
    outbound_body: str | None,
    thread_context: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    role: LLMRole | str = LLMRole.EXECUTOR,
    brand_context: dict | None = None,
) -> dict:
    result = generate_reply_assistant_draft_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        lead_email=lead_email,
        classification_label=classification_label,
        classification_summary=classification_summary,
        next_action_suggestion=next_action_suggestion,
        should_escalate_reviewer=should_escalate_reviewer,
        outbound_subject=outbound_subject,
        outbound_body=outbound_body,
        thread_context=thread_context,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        role=role,
        brand_context=brand_context,
    )
    if result.parsed is None:
        return _reply_assistant_draft_fallback(subject).model_dump()
    return result.parsed.model_dump()


def _review_reply_assistant_draft_fallback() -> ReplyAssistantDraftReviewResult:
    return ReplyAssistantDraftReviewResult(
        summary="Reviewer analysis unavailable.",
        feedback="No se pudo revisar el draft de forma automática. Conviene revisarlo manualmente.",
        suggested_edits=["Revisar manualmente antes de usar este draft."],
        recommended_action="edit_before_sending",
        should_use_as_is=False,
        should_edit=True,
        should_escalate=True,
    )


def review_reply_assistant_draft_structured(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    reply_should_escalate_reviewer: bool,
    outbound_subject: str | None,
    outbound_body: str | None,
    thread_context: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    draft_subject: str,
    draft_body: str,
    draft_summary: str | None,
    suggested_tone: str | None,
    role: LLMRole | str = LLMRole.REVIEWER,
    target_type: str | None = None,
    target_id: str | None = None,
    tags: dict[str, object] | None = None,
):
    client_module = get_client_module()
    prompt_args = {
        "business_name": sanitize_field(business_name) or "Unknown",
        "industry": sanitize_field(industry) or "Unknown",
        "city": sanitize_field(city) or "Unknown",
        "lead_email": sanitize_field(lead_email) or "Unknown",
        "classification_label": classification_label or "Unknown",
        "classification_summary": sanitize_field(classification_summary)
        or "No classification summary available",
        "next_action_suggestion": sanitize_field(next_action_suggestion)
        or "No next action suggestion available",
        "reply_should_escalate_reviewer": "true" if reply_should_escalate_reviewer else "false",
        "outbound_subject": sanitize_field(outbound_subject) or "Unknown",
        "outbound_body": sanitize_field(outbound_body) or "Unknown",
        "thread_context": sanitize_field(thread_context) or "No previous thread context available",
        "from_email": sanitize_field(from_email) or "Unknown",
        "to_email": sanitize_field(to_email) or "Unknown",
        "subject": sanitize_field(subject) or "No subject",
        "body_text": sanitize_field(body_text) or "No body text available",
        "draft_subject": sanitize_field(draft_subject),
        "draft_body": sanitize_field(draft_body),
        "draft_summary": sanitize_field(draft_summary) or "No draft summary available",
        "suggested_tone": suggested_tone or "Unknown",
    }
    return client_module.invoke_structured(
        function_name="review_reply_assistant_draft",
        prompt=REPLY_ASSISTANT_DRAFT_REVIEW_PROMPT,
        prompt_args=prompt_args,
        role=role,
        fallback_factory=_review_reply_assistant_draft_fallback,
        target_type=target_type,
        target_id=target_id,
        tags=tags,
    )


def review_reply_assistant_draft(
    *,
    business_name: str | None,
    industry: str | None,
    city: str | None,
    lead_email: str | None,
    classification_label: str | None,
    classification_summary: str | None,
    next_action_suggestion: str | None,
    reply_should_escalate_reviewer: bool,
    outbound_subject: str | None,
    outbound_body: str | None,
    thread_context: str | None,
    from_email: str | None,
    to_email: str | None,
    subject: str | None,
    body_text: str | None,
    draft_subject: str,
    draft_body: str,
    draft_summary: str | None,
    suggested_tone: str | None,
    role: LLMRole | str = LLMRole.REVIEWER,
) -> dict:
    result = review_reply_assistant_draft_structured(
        business_name=business_name,
        industry=industry,
        city=city,
        lead_email=lead_email,
        classification_label=classification_label,
        classification_summary=classification_summary,
        next_action_suggestion=next_action_suggestion,
        reply_should_escalate_reviewer=reply_should_escalate_reviewer,
        outbound_subject=outbound_subject,
        outbound_body=outbound_body,
        thread_context=thread_context,
        from_email=from_email,
        to_email=to_email,
        subject=subject,
        body_text=body_text,
        draft_subject=draft_subject,
        draft_body=draft_body,
        draft_summary=draft_summary,
        suggested_tone=suggested_tone,
        role=role,
    )
    if result.parsed is None:
        return _review_reply_assistant_draft_fallback().model_dump()
    return result.parsed.model_dump()
