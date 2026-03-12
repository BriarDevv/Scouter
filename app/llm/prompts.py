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
