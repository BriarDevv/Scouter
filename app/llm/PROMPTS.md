# Prompt Catalog

Quick reference for all registered prompts in the Scouter LLM system.

**Registry:** `app/llm/prompt_registry.py`
**Templates:** `app/llm/prompts.py` (664 lines)
**Contracts:** `app/llm/contracts.py` (Pydantic response schemas)

## Registered Prompts

| Prompt ID | Version | Role | Contract | Purpose |
|-----------|---------|------|----------|---------|
| `lead_quality.evaluate` | v2 | Executor | `LeadQualityResult` | Evaluate lead quality (high/medium/low) with reasoning |
| `business_summary.generate` | v2 | Executor | `BusinessSummaryResult` | Summarize business from enrichment data |
| `commercial_brief.generate` | v2 | Executor | `CommercialBriefResult` | Generate commercial brief with opportunity score |
| `commercial_brief.review` | v2 | Reviewer | `CommercialBriefReviewResult` | Review and approve/reject brief |
| `outreach_draft.generate` | v2 | Executor | `OutreachDraftResult` | Generate personalized outreach email |
| `outreach_draft.review` | v2 | Reviewer | `OutreachDraftReviewResult` | Review draft for tone, accuracy, personalization |
| `whatsapp_draft.generate` | v2 | Executor | `WhatsAppDraftResult` | Generate WhatsApp outreach message |
| `lead_review.generate` | v2 | Reviewer | `LeadReviewResult` | Review and adjust lead quality rating |
| `reply_assistant_draft.generate` | v2 | Executor | `ReplyAssistantDraftResult` | Draft reply to inbound message |
| `reply_assistant_draft.review` | v2 | Reviewer | `ReplyAssistantDraftReviewResult` | Review reply draft |
| `inbound_reply.classify` | v2 | Reviewer | `ReplyClassificationResult` | Classify inbound reply intent |
| `inbound_reply.review` | v2 | Reviewer | `InboundReplyReviewResult` | Review inbound classification |
| `dossier.generate` | v2 | Executor | `DossierResult` | Generate detailed lead dossier |

## Non-Registry Prompts

| Location | Prompt ID | Role | Purpose |
|----------|-----------|------|---------|
| `app/llm/prompts.py` | `CLOSER_RESPONSE_SYSTEM` | Agent (Mote) | WhatsApp closer conversation |
| `app/agent/scout_prompts.py` | `SCOUT_SYSTEM_PROMPT` | Agent (Scout) | Investigation protocol |
| `app/workers/weekly_tasks.py` | `weekly_synthesis` | Executor | Weekly report natural language synthesis |

## Prompt Structure

Each registered prompt has:
- **System prompt** (`*_SYSTEM`): Instructions for the model (trusted, no external data)
- **Data template** (`*_DATA`): Template filled with external data (`<external_data>` tags)
- **Contract**: Pydantic model that validates the JSON response
- **Fallback**: Default values returned when LLM fails completely

## Correction Output

Review prompts (Reviewer role) output structured corrections:
```json
{"category": "tone|cta|personalization|length|accuracy|relevance|format|language",
 "severity": "critical|important|suggestion",
 "issue": "what was wrong",
 "suggestion": "how to fix"}
```
Persisted to `review_corrections` table, aggregated for prompt improvement recommendations.

## Adding a New Prompt

1. Add system + data templates to `app/llm/prompts.py`
2. Add Pydantic contract to `app/llm/contracts.py`
3. Register `PromptDefinition` in `app/llm/prompt_registry.py`
4. Create invocation function in `app/llm/client.py` or `app/llm/invocations/`
5. Update this catalog
