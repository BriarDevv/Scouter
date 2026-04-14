# Scouter — Repo Hardening Plan

Roadmap derivado de `docs/audits/repo-deep-audit.md` (2026-04-13).
Objetivo: convertir un pipeline con score 6.3/10 en 7.8/10 en ~3-4 semanas, sin rediseño.

Ordenados por **impacto / costo** (mayor ROI primero). Cada ítem tiene scope, entry-points, verificación.

---

## Phase 1 — Stop the bleeding (Week 1)

### 1.1 Fix crítico del geo bug CABA→USA
**Scope**: evitar que el crawler devuelva negocios fuera del país del territorio.
**Files**:
- `app/crawlers/google_maps_crawler.py:195-199` — agregar al body:
  - `regionCode: "AR"` (configurable por territorio).
  - `locationBias.circle` usando `get_coords(city)` de `app/data/cities_ar.py:95`.
- `app/crawlers/google_maps_crawler.py:106-160` — post-filter: descartar `place` si `formattedAddress` no contiene token de país/provincia esperado.
- Import de `get_coords` en el crawler.

**Test de regresión**:
- `tests/crawlers/test_google_maps_crawler.py`: mock Places API; `crawl("CABA", ...)` no debe devolver `place.addressComponents.country != "AR"`.

**Commit**: `fix(crawlers): anchor Google Places queries to territory country and coords`
**Impacto**: elimina 90% del leak. Previene reputational + budget damage.

---

### 1.2 Idempotency guards en research/brief/reply drafts
**Scope**: evitar duplicados en re-run.
**Files**:
- `app/workers/research_tasks.py:28` — check si existe `LeadResearchReport` SUCCEEDED reciente antes de disparar Scout.
- `app/workers/brief_tasks.py:32` — check `CommercialBrief` existente antes de generar.
- `app/services/inbox/reply_response_service.py` — check `ReplyAssistantDraft` PENDING_REVIEW para ese `inbound_message_id`.

**Commit**: `feat(workers): add idempotency guards to research/brief/reply draft tasks`
**Impacto**: ahorra LLM cost en re-runs, evita ruido en UI.

---

### 1.3 Retries sensatos en beat tasks
**Scope**: un hipo de Redis no debe perder 30min.
**Files**:
- `app/workers/auto_pipeline_tasks.py:18` — `max_retries=2, retry_backoff=True`.
- `app/workers/inbox_tasks.py:15` — igual.
- `app/workers/growth_tasks.py` — igual para `task_growth_cycle`.

**Commit**: `fix(workers): add retries to beat tasks to survive transient broker hiccups`

---

## Phase 2 — Wire the loops (Week 2)

### 2.1 Auto-replenish fuera de cron
**Scope**: cuando no hay leads NEW, disparar crawl en vez de dormir.
**Files**:
- `app/workers/auto_pipeline_tasks.py:47-49` — en lugar de `return`, si `auto_replenish_enabled` y hay territorios activos no-saturados → `task_crawl_territory.delay(territory_id)` para el menos recientemente crawleado.
- Nuevo setting `OperationalSettings.auto_replenish_enabled` (default True).
- Respetar backpressure + cap (1 crawl por tick).

**Commit**: `feat(pipeline): auto-replenish territories when new leads queue is empty`
**Impacto**: quita el "duerme hasta lunes 8am" en weekends.

---

### 2.2 DLQ replay task
**Scope**: drenar `DeadLetterTask`.
**Files**:
- Nueva beat task `app/workers/janitor.py:task_drain_dlq` (cada 1h).
- Query `DeadLetterTask WHERE replayed_at IS NULL AND created_at > now() - 24h`.
- Re-dispatcha via `task_name` lookup (limite 10 por tick).
- Set `replayed_at = now()`.

**Commit**: `feat(workers): implement DLQ drain task for automatic replay`

---

### 2.3 Follow-up chain básica
**Scope**: lead CONTACTED sin respuesta → follow-up draft o escalada a humano.
**Files**:
- Nueva task `app/workers/followup_tasks.py:task_check_followup` (beat cada 6h).
- Query `Lead WHERE status=CONTACTED AND updated_at < now() - followup_days AND no inbound_message`.
- Genera `ReplyAssistantDraft` con template de follow-up + notifica operador.
- Setting `OperationalSettings.followup_days` (default 3).

**Commit**: `feat(outreach): add automatic follow-up chain for non-responding leads`
**Impacto**: cierra un gap enorme de producto. Cada lead CONTACTED sin follow-up es lead muerto.

---

## Phase 3 — Know what it costs (Week 3)

### 3.1 Cost tracking per LLM invocation
**Scope**: medir tokens + USD por invocación.
**Files**:
- `app/models/llm_invocation.py` — agregar columnas `prompt_tokens`, `completion_tokens`, `usd_cost_estimated`.
- Alembic migration.
- Wrapper en `app/llm/invocations/` que capture metrics post-call.
- Tabla `cost_per_lead_view` (materialized view) que agrupe por `pipeline_run.lead_id`.

**Commit**: `feat(llm): track tokens and estimated USD cost per invocation`

---

### 3.2 Budget kill-switch
**Scope**: apagar pipeline si budget diario excedido.
**Files**:
- `OperationalSettings.daily_usd_budget` (nullable).
- Check al inicio de `task_full_pipeline`: sumar cost del día; si > budget → mark skipped + notificación critical.

**Commit**: `feat(settings): add daily USD budget kill-switch`

---

## Phase 4 — See in the dark (Week 3-4)

### 4.1 Event-store de transiciones
**Scope**: tabla inmutable de eventos de lead (status transitions, pipeline steps, outreach events).
**Files**:
- Nueva tabla `lead_events` (id, lead_id, event_type, old_status, new_status, payload_json, ts, actor).
- Hooks en:
  - `app/services/leads/lead_service.py:update_lead_status`.
  - `app/workers/pipeline_tasks.py` — escribir en cada `mark_task_*`.
  - `app/services/outreach/outreach_service.py`.
- Vista dashboard simple `/leads/[id]/timeline`.

**Commit**: `feat(models): add lead_events table for immutable transition history`
**Impacto**: debugging forense y base para ML future.

---

### 4.2 Alert channels externos
**Scope**: Telegram/Slack/email notif para severidad critical.
**Files**:
- `app/services/notifications/notification_emitter._emit` — si severity=critical AND canal configurado → dispatch webhook.
- Settings por canal (`OperationalSettings.telegram_critical_webhook`, etc.).
- Dedup por `dedup_key` (ya existente).

**Commit**: `feat(notifications): wire external alert channels for critical severity`

---

### 4.3 On-startup recovery scan
**Scope**: al arrancar FastAPI, escanear pipelines huérfanos sin esperar al janitor.
**Files**:
- `app/main.py:29-32` (lifespan) — llamar `sweep_stale_tasks()` una vez al arranque.
- Log `startup_recovery_complete` con conteos.

**Commit**: `feat(main): run janitor sweep on startup to recover from crashes immediately`

---

## Phase 5 — Clean the semantics (Week 4)

### 5.1 Auto-des-saturación de territorios
**Scope**: territorios saturados >60d sin crawl se resetan.
**Files**:
- Nueva beat task mensual `task_unsaturate_old_territories`.
- Filtro: `is_saturated=True AND last_crawled_at < now() - 60d AND NOT manual_never_unsaturate`.
- Setear `is_saturated=False`, `last_dup_ratio=NULL`.

**Commit**: `feat(territories): auto-unsaturate territories not crawled in 60 days`

---

### 5.2 Consolidar STEP_CHAIN en single source
**Scope**: eliminar duplicación entre `janitor.py:42-53` y resume endpoint.
**Files**:
- Nuevo `app/workflows/step_chain.py` con `PIPELINE_STEP_CHAIN` dict.
- `janitor.py` y `api/v1/pipelines.py` importan de ahí.

**Commit**: `refactor(workflows): consolidate pipeline step chain into single module`

---

### 5.3 Narrative fix en docs
**Scope**: dejar de llamarle "Agent OS" mientras no haya closed-loop learning.
**Files**:
- `README.md:24` — reemplazar "AI Agent OS" por "LLM ops pipeline with 2 specialized agents".
- `docs/agents/hierarchy.md` — clarificar que Executor/Reviewer son "roles" no "agents".
- Mantener `IDENTITY.md` y `SOUL.md` como runtime persona (no cambio).

**Commit**: `docs(readme): clarify agent OS framing - 2 agents + 2 LLM roles, not 4 agents`

---

## Success Metrics (post Phase 5)

- **Geo reliability**: 0% leads cuyo `formattedAddress.country != territory.country` en muestra de 200 leads.
- **Self-replenish**: uptime de "queue non-empty" > 95% en 7 días.
- **DLQ drain**: `DeadLetterTask WHERE replayed_at IS NULL AND created_at < now() - 2h` debería ser < 5% del total.
- **Follow-up coverage**: % de leads CONTACTED con al menos 1 follow-up en 7 días > 80%.
- **Cost tracking**: 100% de `LLMInvocation` rows tienen `prompt_tokens != NULL`.
- **Recovery**: tiempo desde crash a "pipeline running again" bajo 2min (vs ~15min actual).
- **Autonomy score re-audit**: 7.8+ (vs 4.6 actual).

---

## What NOT to do (anti-scope)

- **NO rediseñar Celery → Temporal/DurableFunctions.** El ROI no compensa la complejidad en esta escala.
- **NO implementar "AI team meetings" multi-agente hasta tener cost tracking + feedback loop + 500+ outcomes limpios.**
- **NO migrar Ollama a providers pagos "porque el 27b es lento".** Arreglar retries + batching es más barato que reescribir el stack LLM.
- **NO reescribir scoring con ML todavía.** La data está contaminada por el geo bug; sin datos limpios, ML es ruido.
- **NO tocar `SOUL.md` / `IDENTITY.md` salvo wiring.** Son runtime assets, no docs.

---

## Order of execution (suggested)

| Week | Focus | Commits aprox |
|---|---|---|
| 1 | Geo fix + idempotency + retries (Phase 1) | 3-5 |
| 2 | Replenish + DLQ replay + follow-up (Phase 2) | 3-4 |
| 3 | Cost tracking + budget kill-switch + event-store start (Phase 3 + 4.1) | 3-5 |
| 4 | Alerts + startup recovery + des-saturación + narrative (Phase 4.2-5) | 4-6 |

Total: ~15-20 commits conventional-style en ~4 semanas de dev dedicado.
