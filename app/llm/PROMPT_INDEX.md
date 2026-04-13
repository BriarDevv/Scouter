# Scouter Prompt Index

All prompts used by the system, across both the LLM invocation layer and the Agent system.

## LLM Invocation Prompts (`app/llm/prompts/`)

| Prompt | File | Role | Purpose |
|--------|------|------|---------|
| `ANTI_INJECTION_PREAMBLE` | `system.py` | System (shared) | Security preamble injected into all LLM prompts to prevent prompt injection from external data |
| `CLOSER_RESPONSE_SYSTEM` | `system.py` | System | Mote WhatsApp closer persona — short, rioplatense sales responses |
| `SUMMARIZE_BUSINESS_SYSTEM` / `_DATA` | `lead.py` | System / User | Business analyst summary of a lead's digital presence and opportunity |
| `EVALUATE_LEAD_QUALITY_SYSTEM` / `_DATA` | `lead.py` | System / User | Sales qualification scoring (high/medium/low) with reasoning and suggested angle |
| `GENERATE_OUTREACH_EMAIL_SYSTEM` / `_DATA` | `outreach.py` | System / User | Cold outreach email generation with rioplatense tone and signal-based angles |
| `GENERATE_WHATSAPP_DRAFT_SYSTEM` / `_DATA` | `outreach.py` | System / User | Short WhatsApp outreach message generation (max 300 chars) |
| `CLASSIFY_INBOUND_REPLY_SYSTEM` / `_DATA` | `reply.py` | System / User | Classify inbound sales replies (interested, not_interested, etc.) with confidence |
| `GENERATE_REPLY_ASSISTANT_DRAFT_SYSTEM` / `_DATA` | `reply.py` | System / User | Draft reply emails for inbound messages with tone matching |
| `DOSSIER_SYSTEM` / `_DATA` | `research.py` | System / User | Structured business dossier generation from research data |
| `COMMERCIAL_BRIEF_SYSTEM` / `_DATA` | `research.py` | System / User | Internal commercial brief with opportunity score, scope, and contact method |
| `REVIEW_LEAD_SYSTEM` / `_DATA` | `review.py` | System / User | Senior reviewer second opinion on lead evaluation and scoring |
| `REVIEW_OUTREACH_DRAFT_SYSTEM` / `_DATA` | `review.py` | System / User | Senior reviewer pass on outreach draft quality (approve/revise/skip) |
| `REVIEW_INBOUND_REPLY_SYSTEM` / `_DATA` | `review.py` | System / User | Senior reviewer deep second opinion on inbound reply classification |
| `REVIEW_REPLY_ASSISTANT_DRAFT_SYSTEM` / `_DATA` | `review.py` | System / User | Premium reviewer validation of assisted reply drafts (use_as_is/edit/escalate) |
| `REVIEW_COMMERCIAL_BRIEF_SYSTEM` / `_DATA` | `review.py` | System / User | Senior commercial reviewer validation of generated briefs |
| `BATCH_REVIEW_SYNTHESIS_SYSTEM` / `_DATA` | `review.py` | System / User | Batch performance analysis — strategy brief and improvement proposals |
| `BATCH_REVIEW_VALIDATION_SYSTEM` / `_DATA` | `review.py` | System / User | Senior validation of batch review synthesis — confidence adjustment and overread detection |

## Agent System Prompts (`app/agent/`)

| Prompt | File | Agent | Purpose |
|--------|------|-------|---------|
| `AGENT_IDENTITY` | `prompts.py` | Mote | Core identity and capabilities of the Mote conversational agent |
| `SECURITY_PREAMBLE` | `prompts.py` | Mote | Anti-injection and credential protection rules for agent tool responses |
| `build_agent_system_prompt()` | `prompts.py` | Mote | Assembles the full system prompt from identity + security + personality (SOUL.md/IDENTITY.md) + tools schema + live system context |
| `SCOUT_SYSTEM_PROMPT` | `scout_prompts.py` | Scout | Field investigator agent — browses websites, extracts contacts, analyzes competitors |
| `SCOUT_USER_PROMPT_TEMPLATE` | `scout_prompts.py` | Scout | Per-lead investigation kickoff template with business data |

## Adding a New Prompt

### LLM Invocation Prompt
1. Create in `app/llm/prompts/{domain}.py`
2. Follow `*_SYSTEM` / `*_DATA` naming convention
3. Export from `app/llm/prompts/__init__.py`
4. Create invocation function in `app/llm/invocations/{domain}.py`

### Agent System Prompt
1. Add to `app/agent/prompts.py` (Mote) or `app/agent/scout_prompts.py` (Scout)
2. These are loaded at agent initialization, not through the prompt registry
