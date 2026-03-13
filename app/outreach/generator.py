"""Outreach draft generation using LLM."""

from app.llm.client import generate_outreach_draft as llm_generate
from app.llm.roles import LLMRole
from app.models.lead import Lead


def generate_draft_content(lead: Lead) -> tuple[str, str]:
    """Generate subject and body for an outreach email. Returns (subject, body)."""
    result = llm_generate(
        business_name=lead.business_name,
        industry=lead.industry,
        city=lead.city,
        website_url=lead.website_url,
        instagram_url=lead.instagram_url,
        llm_summary=lead.llm_summary,
        llm_suggested_angle=lead.llm_suggested_angle,
        signals=list(lead.signals),
        role=LLMRole.EXECUTOR,
    )
    return result["subject"], result["body"]
