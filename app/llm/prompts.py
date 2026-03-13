"""Prompt templates for LLM operations. All prompts expect structured JSON output."""

SUMMARIZE_BUSINESS = """You are a business analyst. Given the following lead data, write a brief summary of the business.

Lead data:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Website: {website_url}
- Instagram: {instagram_url}
- Detected signals: {signals}

Respond ONLY with a JSON object:
{{
  "summary": "2-3 sentence summary of the business"
}}"""

EVALUATE_LEAD_QUALITY = """You are a sales qualification expert for a web development agency. Evaluate whether this business is a good prospect for web development/redesign services.

Lead data:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Website: {website_url}
- Instagram: {instagram_url}
- Detected signals: {signals}
- Current score: {score}

Consider:
1. Does this business likely need a website or website improvement?
2. Can they likely afford web development services?
3. Is there a clear pain point we can solve?

Respond ONLY with a JSON object:
{{
  "quality": "high" | "medium" | "low",
  "reasoning": "1-2 sentences explaining your assessment",
  "suggested_angle": "1 sentence suggesting the best sales angle"
}}"""

GENERATE_OUTREACH_EMAIL = """You are a professional copywriter for a web development agency. Write a cold outreach email for the following prospect.

Lead data:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Website: {website_url}
- Instagram: {instagram_url}
- LLM Summary: {llm_summary}
- Suggested angle: {llm_suggested_angle}
- Detected signals: {signals}

Rules:
- Be professional but warm
- Keep it under 150 words
- Reference something specific about their business
- Clearly state the value proposition
- Include a soft call to action
- Do NOT be pushy or salesy
- Write in Spanish (Argentina)

Respond ONLY with a JSON object:
{{
  "subject": "Email subject line",
  "body": "Full email body"
}}"""

REVIEW_LEAD = """You are the senior reviewer model for ClawScout. Review this lead carefully and provide a second opinion for the sales operator.

Lead data:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Website: {website_url}
- Instagram: {instagram_url}
- Detected signals: {signals}
- Current score: {score}
- Existing summary: {llm_summary}
- Existing suggested angle: {llm_suggested_angle}

Rules:
- This is a reviewer pass, not the normal executor pipeline.
- Focus on whether this lead deserves operator attention now.
- Be concise and practical.

Respond ONLY with a JSON object:
{{
  "verdict": "priority" | "worth_follow_up" | "not_now",
  "confidence": "high" | "medium" | "low",
  "reasoning": "2-3 sentences with your reviewer rationale",
  "recommended_action": "1 short operator recommendation",
  "watchouts": ["short list of risks, objections, or missing info"]
}}"""

REVIEW_OUTREACH_DRAFT = """You are the senior reviewer model for ClawScout. Review this draft carefully and provide a second opinion for the sales operator.

Lead data:
- Business name: {business_name}
- Industry: {industry}
- City: {city}
- Website: {website_url}
- Instagram: {instagram_url}
- Detected signals: {signals}
- Existing summary: {llm_summary}
- Existing suggested angle: {llm_suggested_angle}

Draft:
- Subject: {subject}
- Body: {body}

Rules:
- This is a reviewer pass, not the normal executor pipeline.
- Judge whether the draft is ready, needs revision, or should be skipped.
- Be concise and practical.
- If the draft is already strong, keep suggested changes short.

Respond ONLY with a JSON object:
{{
  "verdict": "approve" | "revise" | "skip",
  "confidence": "high" | "medium" | "low",
  "reasoning": "2-3 sentences with your reviewer rationale",
  "strengths": ["short list of strengths"],
  "concerns": ["short list of concerns"],
  "suggested_changes": ["short list of concrete fixes"],
  "revised_subject": "optional improved subject or null",
  "revised_body": "optional improved body or null"
}}"""

CLASSIFY_INBOUND_REPLY = """You are the executor model for ClawScout. Classify this inbound sales reply from a lead and produce a short operator-facing summary.

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
{{
  "label": "one valid label",
  "summary": "short factual summary",
  "confidence": 0.0,
  "next_action_suggestion": "short operator next step",
  "should_escalate_reviewer": false
}}"""
