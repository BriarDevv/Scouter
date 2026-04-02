# Herramientas del Agente Hermes

Este archivo documenta las herramientas locales y configuracion especifica del entorno.

## LLM Models (Ollama local)

| Rol | Modelo | Uso |
|-----|--------|-----|
| LEADER | qwen3.5:4b | Orquestacion, resumenes |
| EXECUTOR | qwen3.5:9b | Clasificacion, drafts, scoring, dossiers, briefs |
| REVIEWER | qwen3.5:27b | Review de calidad, validacion de briefs |
| AGENT | hermes3:8b | Chat interactivo con el usuario |

## Canales de comunicacion

- **Web:** Chat SSE en el dashboard (puerto 3000)
- **Telegram:** Bot API — requiere bot_token + chat_id en settings
- **WhatsApp:** CallMeBot API — requiere phone + api_key en settings

## Servicios externos

- **Google Maps API:** Crawler de negocios por territorio/categoria
- **Kapso API:** Outreach WhatsApp (envio de drafts aprobados)
- **Ollama:** LLM inference local (puerto 11434)

## Queues Celery

| Cola | Tareas |
|------|--------|
| enrichment | task_enrich_lead |
| scoring | task_score_lead |
| llm | task_analyze_lead, task_generate_draft, task_generate_brief |
| reviewer | task_review_lead, task_review_draft, task_review_brief, task_review_inbound_message |
| research | task_research_lead |
| default | task_crawl_territory |
