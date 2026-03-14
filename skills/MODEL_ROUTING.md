# Model Routing Reference

Which model handles what. This is the authoritative reference for ClawScout.

## Models

| Role | Model | Context | Use for |
|---|---|---|---|
| leader | qwen3.5:4b | Fast, small context | Summaries, briefs, prioritization. Always after grounded data. |
| executor | qwen3.5:9b | Medium context | Classification, draft generation, quality evaluation, pipeline tasks. |
| reviewer | qwen3.5:27b | Large context, async | On-demand second opinions. Never auto-invoked. |

## Routing rules

1. **Data queries** → No model. Tool-only via clawscoutctl.py.
2. **Briefs / summaries** → leader (via opsctl.py, which runs tools first).
3. **Draft generation** → executor (via API, async task).
4. **Reply classification** → executor (via API).
5. **Lead/draft/reply review** → reviewer (on-demand, async on this machine).
6. **Outreach email generation** → executor.
7. **Notifications** → No model. Tool-only.
8. **WhatsApp conversation** → No model. Keyword matching + tool queries.
9. **Browser inspection** → No model. Playwright + structured extraction.

## Anti-patterns

- Never use reviewer for routine classification.
- Never use executor for simple data lookups.
- Never use leader without grounded data first (tool-first, leader-after).
- Never auto-invoke reviewer — always on explicit user request.
