# Scouter — Post-Hardening Plan

> **Contexto**: Este documento es el sucesor de `docs/roadmaps/repo-hardening-plan.md`, ejecutado en la sesión Ralph del 2026-04-13. Lo de acá es lo que **queda** después de cerrar Phase 1-2 parcial y mover el score de ~6.3/10 a ~7.0/10.

- **Auditoría base**: `docs/audits/repo-deep-audit.md`
- **Roadmap original**: `docs/roadmaps/repo-hardening-plan.md`
- **Progreso Ralph ejecutado**: `.omc/progress.txt` (session 2026-04-13)

## Qué ya se hizo (commits `e2a714e..a1fa689`, 12 commits)

Cerrados en la sesión Ralph:

| # | Feature | Commit |
|---|---|---|
| 1 | Geo fix CABA→USA (regionCode + locationBias + country filter) | `e2a714e` |
| 2 | Idempotency guard research (24h) | `a101efc` |
| 3 | Idempotency guard brief | `6be13da` |
| 4 | Retries + backoff en beat tasks | `3dc4e47` |
| 5 | DLQ replay task (hourly) | `6848093` |
| 6 | Auto-replenish cuando no hay leads NEW | `8e3b583` |
| 7 | On-startup recovery sweep | `b7738d2` |
| 8 | Auto-des-saturación >60d | `e1db80b` |
| 9 | STEP_CHAIN SSOT | `dc3dfe3` |
| 10 | Architect nits (chain guard + DLQ counter) | `290717a` |
| 11 | Deslop (datetime import hoist) | `a1fa689` |

**Resultado**: 325 → 454 tests passing, ruff limpio, 9 features de hardening entregadas.

---

## Lo que queda — 7 items priorizados por impacto/costo

### 🔴 Alto impacto (ALTA prioridad)

#### Item 1 — Cost tracking per `LLMInvocation` + budget kill-switch

**Problema**: Hoy no sabés cuánto cuesta generar un lead convertido. Un prompt fugitivo o un loop de Scout puede quemar $ sin alerta. Sin este dato no podés cerrar el loop outcomes→scoring ni justificar decisiones de negocio.

**Files a tocar**:
- `app/models/llm_invocation.py` — agregar columnas
- `alembic/versions/m7g8h9i0j1k2_add_cost_tracking.py` — migration
- `app/llm/invocations/base.py` (o wrapper central) — captura de tokens
- `app/models/settings.py` — `daily_usd_budget: Mapped[float | None]`
- `app/workers/pipeline_tasks.py:task_full_pipeline` — check budget al inicio
- `app/services/dashboard/` — nueva vista / query para cost-per-lead

**Esfuerzo**: 2-3 días.

**Impacto**: **+0.4 puntos** al score global. Habilita Item 7 (feedback loop).

---

#### Item 2 — Follow-up chain para leads CONTACTED sin respuesta

**Problema**: Hoy un lead `CONTACTED` sin inbound_message es un lead muerto. Nadie lo escala, nadie lo sigue. Es el agujero más grande de producto.

**Files a crear/tocar**:
- `app/workers/followup_tasks.py` — nueva task `task_check_followup`
- `app/services/outreach/followup_service.py` — lógica de "¿quién necesita follow-up?"
- `app/models/settings.py` — `followup_days: Mapped[int]` (default 3)
- `app/workers/celery_app.py` — beat schedule `check-followup` cada 6h
- `app/services/inbox/reply_response_service.py` — reutilizar para generar draft de follow-up

**Esfuerzo**: 2 días.

**Impacto**: **+0.3 puntos**. Cierra un gap enorme de producto.

---

### 🟡 Medio impacto (MEDIA prioridad)

#### Item 3 — Event-store de transiciones `lead_events`

**Problema**: Hoy el history de un lead se reconstruye de timestamps en la row. Debugging forense es doloroso. Imposible hacer analytics serio.

**Files a crear/tocar**:
- `app/models/lead_event.py` — nueva tabla
- `alembic/versions/o9i0j1k2l3m4_add_lead_events.py` — migration
- `app/services/leads/lead_service.py:update_lead_status` — hook de emisión
- `app/workers/pipeline_tasks.py:mark_task_*` — hook en cada transición
- `app/services/outreach/outreach_service.py` — hook en `send_draft`
- `dashboard/app/leads/[id]/timeline/page.tsx` — nueva vista

**Esfuerzo**: 2-3 días.

**Impacto**: **+0.3 puntos**. Base para ML futuro.

---

#### Item 4 — Alert channels externos (Telegram/Slack/email)

**Problema**: Hoy las notificaciones son DB-only. En un stall, nadie se entera hasta que alguien entra al dashboard.

**Files a tocar**:
- `app/services/notifications/notification_emitter.py:_emit` — webhook dispatch en severity=critical
- `app/services/notifications/webhook_dispatcher.py` — nuevo módulo
- `app/models/settings.py` — `telegram_critical_webhook`, `slack_critical_webhook`, `email_critical_recipients`
- `tests/test_notification_webhooks.py` — tests con HTTP mocks

**Esfuerzo**: 1 día.

**Impacto**: **+0.2 puntos**. Lo más barato que saca del modo "monitoreo ciego".

---

### 🟢 Bajo impacto / calidad (BAJA prioridad)

#### Item 5 — Narrative fix en README / docs

**Problema**: El README vende "AI Agent OS con 4 roles" pero en realidad son 2 agentes reales (Mote, Scout) + 2 invocaciones LLM stateless (Executor, Reviewer). Deuda narrativa con el usuario.

**Files a tocar**:
- `README.md:24` — reemplazar framing
- `docs/agents/hierarchy.md` — clarificar roles vs agents
- `docs/agents/identities.md` — disclaimer técnico

**Esfuerzo**: 30 min.

**Impacto**: **+0.1 puntos** (cosmético pero importante para honestidad).

---

#### Item 6 — Territory `country_code` + `bbox` para multi-país

**Problema**: Hoy el geo fix está hardcoded a AR. Para expandir a otros países hace falta parametrizar.

**Files a tocar**:
- `app/models/territory.py` — agregar `country_code`, `center_lat`, `center_lng`, `bbox`
- `alembic/versions/p0j1k2l3m4n5_territory_geo_fields.py` — migration
- `app/crawlers/google_maps_crawler.py:_search_text` — usar `Territory.country_code` + `locationRestriction.rectangle`
- `app/services/territories/geocoding_service.py` — nuevo servicio de pre-geocoding al crear territorio
- `dashboard/components/settings/territories-section.tsx` — UI country picker

**Esfuerzo**: 1-2 días.

**Impacto**: **+0.1 puntos**. Sólo si planean expandir fuera de AR.

---

#### Item 7 — Janitor split (refactor puro)

**Problema**: `app/workers/janitor.py` tiene 540+ líneas. Scope creep real: hace stale sweep + zombies + territory + DLQ + batch review.

**Files a crear/tocar**:
- `app/workers/janitor/__init__.py` — re-exports
- `app/workers/janitor/stale.py` — sweep_stale_tasks core
- `app/workers/janitor/zombies.py` — sweep_zombie_leads + stuck research
- `app/workers/janitor/territory.py` — sweep_unsaturate_old_territories
- `app/workers/janitor/dlq.py` — drain_dead_letter_queue
- Sin cambios de comportamiento; sólo movimiento.

**Esfuerzo**: 1 día.

**Impacto**: **0 puntos** al score operativo, pero mejora mantenibilidad.

---

## Deferred / NO hacer todavía

Estos items aparecen en el audit pero **no** tienen sentido ejecutarlos hasta que otras piezas estén listas.

| Item | Por qué no ahora |
|---|---|
| **Feedback loop outcomes → scoring con ML** | Requiere 500+ outcomes limpios + cost tracking + geo bug resuelto (✅). Sin los primeros dos, es especular con datos contaminados. |
| **AI team meetings con consenso multi-agente** | Requiere experience memory (embedding store) + cost tracking + feedback loop. Hasta ese punto es teatro. |
| **Rediseño Celery → Temporal/DurableFunctions** | ROI no justifica la complejidad a esta escala. El hardening actual cierra 80% del riesgo operativo sin cambiar el stack. |
| **Separar SECRET_KEY vs DB_CRYPTO_KEY** | Cambio arquitectónico con migración de datos. Documentar en ADR cuando haya incidente real. |
| **External secrets manager (Vault, AWS SM)** | Cambio de proceso operativo, no de código. Pospuesto hasta producción real con múltiples operadores. |

---

## Plan de implementación

### Fase A — Visibility primero (semana 1)

Todo lo que saca del modo "monitoreo ciego". Barato, alto ROI.

1. **Item 4** — Alert channels externos (1 día)
2. **Item 1** — Cost tracking + budget kill-switch (2-3 días)

**Outcome**: en ~3-4 días tenés ojos sobre costo y alertas críticas sobre Telegram/Slack.

### Fase B — Cerrar gaps de producto (semana 2)

Lo que más duele al usuario hoy.

3. **Item 2** — Follow-up chain (2 días)
4. **Item 5** — Narrative fix (30 min — hacelo mientras esperás compilación)

**Outcome**: en ~3 días más, los leads CONTACTED sin respuesta se manejan; el README dice la verdad.

### Fase C — Foundation para analytics (semana 3)

Base para la próxima ola de features.

5. **Item 3** — Event-store lead_events (2-3 días)

**Outcome**: forense + base para ML. **En este punto el score proyectado es ~7.8/10**.

### Fase D — Extensiones opcionales (semana 4 o cuando haga falta)

Sólo si el negocio lo pide.

6. **Item 6** — Territory country_code (sólo si expanden fuera de AR, 1-2 días)
7. **Item 7** — Janitor split (cuando haya momento de pausa, 1 día)

---

## Criterios de éxito (por item)

### Item 1 — Cost tracking
- [ ] Toda `LLMInvocation` row tiene `prompt_tokens != NULL` 24h después del deploy.
- [ ] Dashboard muestra costo por lead WON vs LOST.
- [ ] Setting `daily_usd_budget` disparando `notification_emitter` severity=critical cuando se excede.
- [ ] Test: pipeline aborta si cost del día > budget; notificación emitida.

### Item 2 — Follow-up chain
- [ ] % leads CONTACTED sin respuesta con al menos 1 follow-up en 7 días > 80%.
- [ ] Setting `followup_days` respetado (no se dispara antes ni después).
- [ ] Test: lead CONTACTED hace N+1 días → genera `ReplyAssistantDraft` de tipo FOLLOWUP.
- [ ] No follow-up si hay inbound_message en el intermedio.

### Item 3 — Event-store
- [ ] Tabla `lead_events` contiene al menos 1 row por transición real de `Lead.status`.
- [ ] Vista `/leads/[id]/timeline` renderiza el history cronológico.
- [ ] Test: cada `update_lead_status` emite 1 evento.
- [ ] Performance: query de timeline < 100ms con 1000+ eventos por lead.

### Item 4 — Alert channels
- [ ] Setting `telegram_critical_webhook` configurado → notification severity=critical llega a Telegram.
- [ ] Dedup con `dedup_key` evita spam.
- [ ] Test: mock HTTP; verifica POST al webhook con payload correcto.
- [ ] Fallo del webhook **no** tumba `_emit` (logged + continúa).

### Item 5 — Narrative fix
- [ ] `README.md` no menciona "4 AI roles" sin clarificación.
- [ ] `docs/agents/hierarchy.md` distingue explícitamente "agent" vs "LLM role".
- [ ] `ADR-004-honest-agent-framing.md` nuevo ADR documentando la decisión.

### Item 6 — Territory country_code
- [ ] `Territory.country_code` existe y es non-null.
- [ ] Crawler envía `locationRestriction.rectangle` usando `Territory.bbox` cuando disponible.
- [ ] Pre-geocoding genera `center_lat`, `center_lng`, `bbox` al crear territorio.
- [ ] Test: territorio con country_code="US" y bbox sobre California → no retorna places AR.

### Item 7 — Janitor split
- [ ] `app/workers/janitor/` existe como paquete.
- [ ] Ningún archivo en `janitor/` supera 200 LOC.
- [ ] Todos los tests existentes siguen pasando sin cambios.
- [ ] `app/workers/janitor.py` original eliminado o reducido a re-export shim.

---

## Tests requeridos por item (baseline esperado)

| Item | Tests nuevos mínimos | Tests que NO deben romper |
|---|---|---|
| 1 | `test_llm_cost_tracking.py` (~6 tests) | toda la suite actual (454) |
| 2 | `test_followup_chain.py` (~5 tests) | `test_api_leads.py`, `test_inbox_*.py` |
| 3 | `test_lead_events.py` (~8 tests) | `test_idempotency.py`, `test_api_*.py` |
| 4 | `test_notification_webhooks.py` (~4 tests) | `test_notifications.py` si existe |
| 5 | — (doc-only) | — |
| 6 | `test_territory_geo_fields.py` (~5 tests) + extender `test_google_maps_crawler.py` | todo lo actual |
| 7 | — (refactor puro; tests existentes cubren) | todos los janitor-related |

**Total tests nuevos proyectados**: ~28 tests.
**Suite total post-completion proyectada**: ~482 tests.

---

## Score progression proyectado

| Estado | Global | Detalle |
|---|---|---|
| Pre-sesión Ralph (2026-04-13 baseline) | **6.3/10** | Audit original |
| Post-sesión actual | **7.0/10** | 9 features + 2 polish + 1 deslop = este doc es el punto de partida |
| + Item 1 (cost tracking) | 7.3/10 | Visibility operativa |
| + Item 2 (follow-up) | 7.5/10 | Gap de producto cerrado |
| + Item 4 (alerts) | 7.6/10 | Alertas en tiempo real |
| + Item 3 (event-store) | **7.8/10** ← objetivo roadmap original | Forense + ML base |
| + Item 5 (narrative) | 7.9/10 | Honestidad con usuario |
| + Item 6 (territory country_code) | 8.0/10 | Multi-país listo |
| + Item 7 (janitor split) | 8.0/10 | Mantenibilidad, no score |
| + Feedback loop (futuro, no este plan) | 8.3/10 | Con 500+ outcomes limpios |
| + AI meetings reales (futuro lejano) | 8.5/10 | Con experience memory |

---

## Anti-patterns explícitos (NO hacer)

- **NO** agregar features nuevas sin tests de regresión. Sessión anterior probó que 454/454 verde previene drift silencioso.
- **NO** bundlear cambios no relacionados en un solo commit. Conventional commits uno por story.
- **NO** tocar `SOUL.md` o `IDENTITY.md` salvo wiring explícito.
- **NO** modificar `docs/audits/repo-deep-audit.md` o `docs/roadmaps/repo-hardening-plan.md` — son artefactos históricos.
- **NO** usar `rm -rf` o reset destructivo sin confirmación. El proyecto tiene un .env backup pattern que protege secretos.
- **NO** mover imports al top del módulo si hay deferred imports documentados en `AGENTS.md:61-64`.
- **NO** implementar Item 1-7 todos en paralelo. Hay dependencias (Item 1 habilita feedback-loop futuro, Item 3 habilita analytics futuros). Seguí el orden A→B→C→D.

---

## Ejecución sugerida con Ralph

Cada item puede correrse como una mini-campaña Ralph independiente:

```bash
# Ejemplo Item 1
/oh-my-claudecode:ralph seguir docs/roadmaps/post-hardening-plan.md Item 1 (cost tracking).
  Calidad > velocidad. Tests obligatorios. Conventional commits.
  Criterios de éxito: ver sección "Item 1 — Cost tracking" del plan.
```

Cada ejecución Ralph debe:
1. Leer el Item específico del plan.
2. Escribir un PRD dedicado en `.omc/prd.json` con acceptance criteria específicos.
3. Commit-per-story siguiendo conventional commits.
4. Architect verification antes de cerrar.
5. Deslop pass bounded a los files del item.
6. `/oh-my-claudecode:cancel` al terminar.

---

## Checklist rápido (copiar/pegar al empezar)

- [x] Item 1 — Cost tracking per LLMInvocation + budget kill-switch ✓ 6857b68
- [x] Item 2 — Follow-up chain para CONTACTED sin respuesta ✓ a6f933a
- [x] Item 3 — Event-store lead_events ✓ e1c7953 + endpoint e3f9f82
- [x] Item 4 — Alert channels externos (Slack — Telegram/WhatsApp ya existían) ✓ 180f659
- [x] Item 5 — Narrative fix README/docs ✓ c544d9d
- [x] Item 6 — Territory country_code ✓ 34cc7be
- [x] Item 7 — Janitor split ✓ be1291e

**Estado del plan**: 7/7 items completados (sesión 2026-04-13). Ver
`.omc/progress.txt` en cada campaña para detalle + SHAs.

**Total estimado**: ~8-10 días de dev dedicado para cerrar 1-5. Ítems 6-7 suman ~3 días más pero son opcionales.

---

## Referencias

- **Sesión Ralph ejecutada**: `.omc/progress.txt` + commits `e2a714e..a1fa689`
- **PRD Ralph cerrado**: `.omc/prd.json` (10 stories passes:true)
- **Auditoría original**: `docs/audits/repo-deep-audit.md` (11 secciones)
- **Roadmap anterior**: `docs/roadmaps/repo-hardening-plan.md` (Phase 1-5)
- **ADRs arquitectónicos**: `docs/architecture/adrs/`
- **AGENTS.md canónico**: `/AGENTS.md` (reglas para AI coding assistants)

---

*Documento creado 2026-04-13 al cierre de la campaña Ralph de hardening. Siguiente campaña Ralph debe consumir este documento como entrada del scaffold PRD.*
