# Agent OS Skills Registry

**Status:** Current as of 2026-04-04

## Mote (hermes3:8b) — Agent

| Skill | Implementation | Description |
|-------|---------------|-------------|
| Chat | app/agent/core.py | Streaming conversation with operator |
| Tool calling | app/agent/tool_registry.py | 55 tools via Hermes 3 XML format |
| Closer response | app/services/outreach/closer_service.py | WhatsApp conversation with clients |
| Weekly context | app/agent/core.py:_build_system_context | Injects latest weekly report |

## Scout (qwen3.5:9b) — Agent

| Skill | Implementation | Description |
|-------|---------------|-------------|
| browse_page | app/agent/scout_tools.py | Playwright + httpx fallback, extracts text/meta/WhatsApp |
| extract_contacts | app/agent/scout_tools.py | Emails, phones, WhatsApp links from page |
| check_technical | app/agent/scout_tools.py | SSL, mobile, speed, SEO checks |
| take_screenshot | app/agent/scout_tools.py | Playwright screenshot to storage/ |
| search_competitors | app/agent/scout_tools.py | Google search for industry+city |
| finish_investigation | app/agent/scout_tools.py | Signal completion with findings |

## Executor (qwen3.5:9b) — Model

| Skill | Implementation | Prompt ID |
|-------|---------------|-----------|
| Business summary | app/llm/client.py | business_summary.summarize |
| Lead quality eval | app/llm/client.py | lead_quality.evaluate |
| Commercial brief | app/llm/client.py | commercial_brief.generate |
| Outreach draft (email) | app/llm/invocations/outreach.py | outreach_draft.generate |
| WhatsApp draft | app/llm/invocations/outreach.py | whatsapp_draft.generate |
| Dossier | app/llm/client.py | dossier.generate |
| Reply assistant | app/llm/invocations/reply_assistant.py | reply_assistant.draft |
| Weekly synthesis | app/workers/weekly_tasks.py | weekly_synthesis |

## Reviewer (qwen3.5:27b) — Model

| Skill | Implementation | Prompt ID |
|-------|---------------|-----------|
| Review lead | app/llm/client.py | lead.review |
| Review brief | app/llm/client.py | commercial_brief.review |
| Review outreach draft | app/llm/client.py | outreach_draft.review |
| Review reply draft | app/llm/invocations/reply_assistant.py | reply_assistant.review |
| Classify inbound reply | app/llm/invocations/reply_classification.py | inbound_reply.classify |

All reviews output structured corrections (category, severity, issue, suggestion)
persisted to `review_corrections` table.

## Leader (qwen3.5:4b) — Reserved

No active skills. The 4b model is reserved for future use.
Weekly synthesis currently runs on Executor (9b).
