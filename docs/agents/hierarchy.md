# Agent OS Hierarchy

**Status:** Current as of 2026-04-13

## Agent vs LLM Role

Scouter uses the term "agent" strictly for components that **loop over tool calls
and make branching decisions** (Mote, Scout). Components that do a single
prompted call to the model fleet (Executor, Reviewer) are **LLM roles**, not
agents — they don't have state, don't call tools, don't branch.

This distinction matters because:

- Agents can reason across multiple observations; roles cannot.
- Agents can fail in ways that require loop termination and timeouts; roles
  return once or fail once.
- Marketing "4 AI agents" when the system has 2 agents + 2 roles is
  misleading to operators who expect emergent multi-agent behaviour.

See [ADR-004](../architecture/adrs/ADR-004-honest-agent-framing.md) for the
decision rationale.

## Team Structure

```
OPERATOR (human)
    Aprueba drafts, toma control de conversaciones, define reglas
    |
AGENTS (loop + tools + decisiones)
    |
    +-- Mote (hermes3:8b)
    |   Rol: Jefe de operaciones + Closer
    |   Decide: respuestas a clientes, escalamiento a humano
    |   Tools: 55 tools via tool_registry (WhatsApp, email, pipeline, chat)
    |
    +-- Scout (qwen3.5:9b)
        Rol: Investigador de campo
        Decide: qué páginas visitar, cuándo terminar investigación
        Tools: 6 Playwright tools (browse, extract, check, screenshot, competitors, finish)
        Límites: 10 loops, 90s timeout, SSRF protection

MODELS (single-shot, stateless)
    |
    +-- Executor (qwen3.5:9b)
    |   Rol: genera análisis, briefs, drafts
    |   No decide: ejecuta lo que el pipeline le pide
    |
    +-- Reviewer (qwen3.5:27b)
        Rol: revisa y corrige con feedback estructurado
        No decide: aprueba/rechaza con correcciones

RESERVED (sin uso actual)
    |
    +-- Leader (qwen3.5:4b)
        Rol previsto: síntesis semanal
        Estado: el weekly report lo genera Executor, no Leader
```

## Quién decide qué

| Decisión | Quién | Cómo |
|----------|-------|------|
| Procesar un lead | Pipeline (automático) | Celery task chain |
| Calidad del lead | Executor (9b) | evaluate_lead_quality_structured |
| Investigar a fondo | Scout (9b) | research_agent loop con tools |
| Aprobar brief | Reviewer (27b) | review_commercial_brief_structured |
| Aprobar draft | Reviewer (27b) | review_outreach_draft_structured |
| Enviar draft | Operador (safe/assisted) o Mote (outreach/closer) | runtime_mode config |
| Responder cliente | Mote (8b) en closer mode | closer_service.generate_closer_response |
| Escalar a humano | Mote (si objeción o sin respuesta) | intent detection |
| Cambiar scoring weights | Operador (manual) | basado en recommendations |
| Template WhatsApp | Pipeline (automático) | template_selection por señales |

## Lo que NO existe

- Leader no tiene tareas asignadas — el 4b está reservado
- No hay "reuniones" entre agentes — la comunicación es via step_context_json
- No hay memoria persistente de agentes — cada invocación es stateless
- No hay auto-aprendizaje — el operador decide si aplicar recomendaciones
