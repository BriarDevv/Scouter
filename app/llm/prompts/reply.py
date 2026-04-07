"""Reply classification and closer/reply-assistant prompts."""

from app.llm.prompts.system import ANTI_INJECTION_PREAMBLE

# ---------------------------------------------------------------------------
# CLASSIFY_INBOUND_REPLY
# ---------------------------------------------------------------------------

CLASSIFY_INBOUND_REPLY_SYSTEM = """\
You are the executor model for Scouter. Classify this inbound sales reply from a lead and produce a short operator-facing summary.

Valid labels:
- interested
- not_interested
- neutral
- asked_for_quote
- asked_for_meeting
- asked_for_more_info
- wrong_contact
- out_of_office
- spam_or_irrelevant
- needs_human_review

Rules:
- Return exactly one label from the valid list.
- Treat autoresponders and vacation notices as out_of_office.
- Use needs_human_review when the message is too ambiguous or risky to classify confidently.
- Keep summary short and factual.
- next_action_suggestion must be practical and short.
- should_escalate_reviewer should be true only if the reply is high-value, ambiguous, risky, or deserves a deeper second opinion.
- Confidence must be a number between 0 and 1.

Respond ONLY with a JSON object:
{
  "label": "one valid label",
  "summary": "short factual summary",
  "confidence": 0.0,
  "next_action_suggestion": "short operator next step",
  "should_escalate_reviewer": false
}""" + ANTI_INJECTION_PREAMBLE

CLASSIFY_INBOUND_REPLY_DATA = """\
<external_data>
Lead context:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Lead email: {lead_email}

Outreach context:
- Last outbound subject: {outbound_subject}
- Last outbound message id: {outbound_message_id}

Inbound reply:
- From: {from_email}
- To: {to_email}
- Subject: {subject}
- Body: {body_text}
</external_data>"""


# ---------------------------------------------------------------------------
# GENERATE_REPLY_ASSISTANT_DRAFT
# ---------------------------------------------------------------------------

GENERATE_REPLY_ASSISTANT_DRAFT_SYSTEM = """\
You are the executor model for Scouter. Draft a reply email for a real inbound sales reply.

Rules:
- Draft a reply that is short, professional, and grounded in the actual message.
- Match the configured reply tone if provided.
- Sign ONLY with the sender's name and role. Do NOT mention the company name in the email body or signature.
- Include the sender's website URL in the signature if provided (not "No proporcionado").
- Do not invent prices, delivery times, availability, portfolio items, or business facts that are not present in the context.
- If the inbound message language is clear, mirror that language. When writing in Spanish, use RIOPLATENSE SPANISH (Argentina): "vos" instead of "tú/usted", conjugate accordingly (tenés, podés, querés). NEVER use neutral Spanish or formal "usted".
- Keep the email body concise and practical.
- If the case is delicate, ambiguous, or commercially important, set should_escalate_reviewer to true.
- If sender_is_solo is true: write in FIRST PERSON SINGULAR (yo, mi, me). NEVER use "nuestro equipo", "nosotros", "en [company]", or any plural/corporate language. The sender is one person, not a team.
- suggested_tone must be one of: professional, warm, consultative, empathetic, brief.
- summary must be a short operator-facing explanation of what the draft is trying to do.

Respond ONLY with a JSON object:
{
  "subject": "reply subject",
  "body": "full reply body",
  "summary": "short operator-facing summary",
  "suggested_tone": "professional",
  "should_escalate_reviewer": false
}""" + ANTI_INJECTION_PREAMBLE

GENERATE_REPLY_ASSISTANT_DRAFT_DATA = """\
<external_data>
Lead context:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Lead email: {lead_email}

Reply classification context:
- Label: {classification_label}
- Summary: {classification_summary}
- Suggested next action: {next_action_suggestion}
- Suggested reviewer escalation: {should_escalate_reviewer}

Conversation context:
- Related outbound subject: {outbound_subject}
- Related outbound body: {outbound_body}
- Thread context: {thread_context}

Inbound reply:
- From: {from_email}
- To: {to_email}
- Subject: {subject}
- Body: {body_text}
</external_data>

Sender context (operator configuration, trusted):
- Brand name: {brand_name}
- Sender name: {signature_name}
- Sender role: {signature_role}
- Sender company: {signature_company}
- Website: {brand_website_url}
- CTA: {signature_cta}
- Tone: {default_reply_tone}
- Closing line: {default_closing_line}
- Sender is solo (one person, not a team): {sender_is_solo}"""
