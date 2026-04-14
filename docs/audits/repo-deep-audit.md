# Scouter — Forensic Deep Audit

Fecha: 2026-04-13
Auditor: Principal Systems Auditor + Pipeline Reliability Engineer + Growth Ops Investigator
Alcance: pipeline end-to-end, territorios, autonomía, observabilidad, calidad de leads, agent OS, idea de "reuniones entre IAs".
Método: evidencia (`file:line`), confidence (HIGH/MED/LOW), impact (HIGH/MED/LOW). Sin chamuyo.

---

## 1. Executive Truth

- **Scouter es un pipeline LLM bien ingenierizado, no un Agent OS.** El framing de "4 agentes IA" es 70% marketing: Mote y Scout son agénticos de verdad; Executor y Reviewer son invocaciones LLM stateless con prompts distintos sobre el **mismo modelo qwen3.5:9b** (según `app/core/config.py:24-25` + readme).
- **Funciona y es trazable**, con buen structlog, accumulated context real (`PipelineRun.step_context_json`), dedup hash estricto, janitor que detecta stuck leads, DLQ tabla, backpressure check, y modo LOW_RESOURCE. **Eso no es poco.**
- **Tres mentiras operativas peligrosas**:
  1. "Autonomía real": el sistema **se queda sin trabajo y no se reabastece solo** fuera de los cron Mon+Thu 8am (`app/workers/celery_app.py:95`). Entre medio idling = horas/días muertos si la saturación cae en mal momento.
  2. "Anti-zombie": la tabla `DeadLetterTask` se escribe pero **nunca se reprocesa** — es una morgue, no un recovery. Confirmado por grep: cero replay logic.
  3. "Reviewer como quality gate": el review corre async y **no bloquea el envío** — las correcciones se loguean pero la aprobación de draft no depende del reviewer (`app/workers/review_tasks.py`).
- **La mentira más peligrosa que el proyecto se puede estar contando a sí mismo**: que "genera leads de calidad automáticamente". Scoring invertido (mal website = más puntaje — *intencional pero sin medir conversión*), sin MX check, sin validación de teléfono, sin filtro geográfico, sin feedback loop de outcomes al scoring. Volumen sí; calidad sin evidencia.
- **Mayor fortaleza real**: accumulated context + tracing por correlation_id + idempotencia por timestamp en 3 de las etapas centrales (enrich/score/analyze). Esto es mejor que el promedio de la industria para un proyecto de este tamaño.
- **Mayor riesgo**: el bug de territorios CABA→USA. Es 100% nuestra culpa (query construction sin `locationBias` ni `regionCode=AR`). Contamina la DB, quema presupuesto de Google Places, y envía outreach a negocios equivocados. Es crítico y sencillo de arreglar.
- **Veredicto corto**: no rediseñar. **Hardening quirúrgico** de 5-7 fixes resuelve el 80% del riesgo.

---

## 2. Pipeline Reality Map

Arquitectura real: **Celery Beat + implicit chaining vía `.delay()`**, no orquestador durable (Temporal/DurableFunctions). `pipeline_run_id` es el hilo que cose las etapas; `PipelineRun.step_context_json` es el shared state.

| # | Stage | Entry (file:line) | Input | Output | Handoff | Idempotent | Retry | Robustez |
|---|---|---|---|---|---|---|---|---|
| 1 | Arranque auto | `auto_pipeline_tasks.py:20` | beat every 30min | PipelineRun queued | `task_full_pipeline.delay()` | NO (*1) | `max_retries=0` | **Frágil** |
| 2 | Enrichment | `pipeline_tasks.py:43` | lead_id + run_id | signals + `enriched_at` | `task_score_lead.delay()` | SÍ (enriched_at) | 3x exp backoff | **Sólida** |
| 3 | Scoring | `pipeline_tasks.py:148` | lead_id | score + `scored_at` | `task_analyze_lead.delay()` | SÍ (scored_at) | 3x exp backoff | **Sólida** |
| 4 | LLM Analysis | `pipeline_tasks.py:258` | lead_id + context | quality/summary | `task_research_lead` if HIGH else `task_generate_draft` | SÍ (llm_summary) | 2x | **Sólida** |
| 5 | Research (Scout) | `research_tasks.py:28` | lead_id | InvestigationThread + findings | `task_generate_brief` | **NO** | 1x | **Frágil** — re-run duplica |
| 6 | Brief Gen | `brief_tasks.py:32` | context | CommercialBrief | `task_review_brief` | **NO** | 1x | **Frágil** |
| 7 | Brief Review | `brief_tasks.py:129` | brief_id | REVIEWED status | `task_generate_draft` | N/A | 1x | **Engañosa** — chain continúa aunque falle |
| 8 | Draft Gen | `pipeline_tasks.py:437` | full context | OutreachDraft | batch_review check; pipeline terminal | SÍ (existing draft) | 2x | **Sólida** |
| 9 | Outreach Send | `mail_service.send_draft` / `outreach_service.py:44` | APPROVED draft | OutreachDelivery + status=CONTACTED | — | Por delivery_id | — | **MED** — mote fallback implícito |
| 10 | Inbox Sync | `inbox_tasks.py:15` | beat every 15min | InboundMessage | `dispatch_classification` | SÍ (dedup_key) | 1x | **Sólida** |
| 11 | Reply Classify | `classification_dispatch.py:21` | InboundMessage | classification_label | auto-draft if positive | N/A | No | **Sólida** |
| 12 | Reply Draft | `reply_response_service.py` | classified msg | ReplyAssistantDraft | manual approve | **NO** | No | **Frágil** |
| 13 | Follow-up | **NO EXISTE** | — | — | — | — | — | **INCOMPLETA — feature faltante** |
| 14 | Resume | `janitor.py:64` + `api/v1/pipelines.py:107` | orphan pipelines | next_task.delay() | step_chain dict | N/A | solo retryable | **MED** — reactivo, 30min latencia |
| 15 | Replenish | `batch_pipeline.py:98` + `crawl_tasks.py:65` (Mon/Thu 8am) | saturated check | new territory crawl | — | — | max 3 rondas | **Frágil** — hard stop |

(*1) `task_full_pipeline` con `max_retries=0` → si falla el dispatch, muere silencioso. Confirmado `auto_pipeline_tasks.py:18`.

---

## 3. Operational Behavior

### ¿Puede arrancar solo?
**Sí, pero con gatillo humano de configuración.** Beat dispara `task_auto_process_new_leads` cada 30min (`celery_app.py:99`). Requiere `OperationalSettings.auto_pipeline_enabled=true`. Si no hay leads nuevos → `return {"status": "ok", "dispatched": 0}` y el beat no vuelve a hacer nada hasta el próximo tick. **Confidence HIGH**.

### ¿Puede seguir corriendo solo?
**Sí, durante horas, siempre que haya leads NEW sin procesar.** Problema: **no genera leads** por su cuenta fuera del cron Mon+Thu 8am. Entre crawls programados puede estar dormido. **Confidence HIGH**.

### ¿Puede reabastecerse solo?
**Parcialmente.** `batch_pipeline.py:98` tiene lógica de "si no hay leads + hay territorios activos/no-saturados → dispara crawl", pero:
- Cap hardcoded de **3 rondas de crawl** antes de rendirse.
- Depende de `Territory.is_saturated=False`. La saturación se dispara si dos crawls seguidos dan dup_ratio > 0.8 (`territory_crawl.py:256`). Una vez saturado, nunca se auto-des-satura: requiere intervención humana.
- `task_auto_process_new_leads` NO llama crawl; solo dispatch de leads NEW existentes. **Gap clave.**

**Veredicto**: self-replenish es **semi-automático**. Es honesto decir que "casi funciona solo" pero no "autónomo de verdad".

### ¿Se queda sin trabajo?
**Sí**, en dos escenarios:
1. Todos los territorios saturados → nada corre hasta Mon/Thu 8am.
2. Queue depth > 50 (`auto_pipeline_tasks.py:35`) → skip por backpressure. Si queue se atasca con tareas lentas, nunca se despacha más. **Este es el loop silencioso más peligroso.**

### ¿Entra en loops?
No encontré loops infinitos, pero hay **retry silencioso en janitor**: si un pipeline es "retryable" (patrones hardcoded en `janitor.py:23-40`) y retry_count < 2, se reanima. **Confidence HIGH**. El cap de 2 evita el loop eterno. ✓

### ¿Genera duplicados?
- **Research + Brief + Reply drafts**: SÍ, si re-corren sin guard de idempotencia (confirmado — no hay check de `research_report_id` existente).
- **Enrichment + Score + Analyze + Draft**: NO, protegidos por timestamp guards.
- **Leads**: dedup hash estricto (`lead_service.py:16-24` `sha256(name|city|website)`) — pero **mismo negocio en otra ciudad = otro lead**. Mismo negocio sin website = potencial duplicado.

### ¿Gasta recursos sin producir valor?
**Sí, potencialmente**:
- Scout research se re-dispara sin guard → quema Playwright + LLM en runs redundantes.
- Enrichment llama APIs externas (HTTP, MX implícito si existiera) — si crash a mitad de proceso, re-run duplica llamadas.
- **Sin cost tracking** (`LLMInvocation` no tiene columna `tokens` ni `usd_cost` — confirmado). No hay circuit breaker por presupuesto.

### ¿Deja estados muertos?
**Sí**:
- Leads pueden quedar en `ENRICHED` si scoring falla post-janitor. Janitor los detecta >1h (`janitor.py:155`) pero solo **loguea warning**, no remedia.
- `DRAFT_READY` con draft `PENDING_REVIEW` >48h → emite notificación, no auto-resuelve.
- `DeadLetterTask` se inserta (`_helpers.py:76`) pero nunca se procesa.

### ¿Puede retomar después de reinicio?
**Parcial**:
- Celery `task_acks_late=True` + `task_reject_on_worker_lost=True` (`celery_app.py:61-62`) → tasks mid-flight vuelven al broker si worker muere.
- **NO hay on-startup scan** (`main.py:29-32` solo loguea).
- Si worker muere entre commit y ack → riesgo de **doble ejecución** (riesgo medio por idempotencia parcial).

### ¿Qué tan dependiente sigue siendo del humano?
- Config inicial (territorios, API keys, settings): **humano obligatorio**.
- Operación diaria: humano para revisar drafts, approve outreach, responder clientes en modo "closer", des-saturar territorios, reprocesar DLQ.
- **Estimación: ~40-50% del día operativo requiere operador.** Más cerca de "cockpit" que "piloto automático".

---

## 4. Territory & Geo Audit — CABA → USA

**Veredicto corto**: **100% culpa nuestra. Google no miente, nosotros no le decimos qué queremos.**

### Trace completo (CABA → resultados USA)

1. **UI/DB**: territorio se guarda como lista de strings en `territories.cities` JSON (`app/models/territory.py`, `app/schemas/territory.py`). **Sin lat/lng, sin country code.**
2. **Workflow**: `territory_crawl.py:173` itera `territory.cities` y pasa `city="CABA"` al crawler.
3. **Crawler query** (`google_maps_crawler.py:92-97`):
   ```python
   location = f"{zone}, {city}" if zone else city
   query = f"{cat} en {location}"   # "restaurante en CABA"
   ```
4. **API body** (`google_maps_crawler.py:195-199`):
   ```python
   body = {
       "textQuery": query,
       "languageCode": "es",
       "maxResultCount": min(max_results, 20),
   }
   ```

### Parámetros AUSENTES (que arreglarían el bug)

| Parámetro | Estado | Efecto esperado |
|---|---|---|
| `locationBias.circle` (lat+lng+radius) | **FALTA** | Priorizaría resultados cerca de BA |
| `locationRestriction.rectangle` | **FALTA** | Restringiría resultados al bbox de CABA |
| `regionCode` = "AR" | **FALTA** | Sesgo fuerte hacia Argentina |
| `includedType` / filtro por category | **FALTA** | Reduciría ambigüedad |
| Post-filter por `formattedAddress` / `addressComponents.country` | **FALTA** | Descartaría resultados USA |

### El detalle que duele
**`app/data/cities_ar.py:7-97` YA TIENE el mapa `CITY_COORDS` con `"CABA": (-34.6037, -58.3816)` y una función `get_coords(city)`.**

Grep confirma:
- Usado en `app/api/v1/dashboard.py:54` (para pintar mapa en el dashboard).
- Usado en `app/services/growth/adjacency.py:203-241` (sugerencias de crecimiento).
- **NO usado en `app/crawlers/google_maps_crawler.py`.**

Existe la data. Existe la función. Nadie la conectó al crawler.

### Por qué "CABA" rompe más que otras ciudades
- "CABA" es un **acrónimo**; Google Places lo ve como free text → hace match con "Cabana Bar", "CABA Restaurant" en California, etc.
- Sin `languageCode=es` (sí está) el inglés dominaría aún más. Con `es` igual contamina porque no hay anclaje geográfico.
- Con `regionCode=AR` + locationBias sobre `(-34.6037, -58.3816)` radio 15km → resultados dentro de CABA real.

### Atribución

| Componente | Culpa | Confidence |
|---|---|---|
| Query free-text sin anclaje | NUESTRA CÓDIGO | **HIGH** |
| `CITY_COORDS` existe pero no se usa en crawler | NUESTRA CÓDIGO | **HIGH** |
| Sin post-filter por country en loop `for place in results` | NUESTRA CÓDIGO | **HIGH** |
| Google devuelve global sin restricción | LIMITACIÓN predecible de Places API (comportamiento esperado) | **HIGH** |

**No es "bug nuestro + bug de Google". Es bug nuestro. Google se comporta como documenta.**

### Fixes priorizados

**Quick fix (≤1 hora, cierra el leak principal)**
- En `google_maps_crawler.py:195-199` agregar:
  ```python
  body["regionCode"] = "AR"
  if coords := get_coords(city):
      body["locationBias"] = {"circle": {"center": {"latitude": coords[0], "longitude": coords[1]}, "radius": 15000}}
  ```
- Agregar post-filter en el loop `for place in results`: si `formattedAddress` no contiene "Argentina" ni ninguna provincia/ciudad conocida, descartar.
- **Impacto**: 90% de los USA-leaks desaparecen.

**Fix correcto (1-2 días)**
- Schema de Territory: agregar `country_code` (default "AR"), `bbox` (lat_min/lat_max/lng_min/lng_max), `center_lat/lng`.
- Migración: completar `CITY_COORDS` para territorios existentes.
- Usar `locationRestriction.rectangle` en crawler.
- Normalizar nombres ambiguos: "CABA"/"Capital Federal"/"Ciudad Autónoma de Buenos Aires" → canonizar a un solo key antes de geocode.
- Unit test: `crawl("CABA", ...)` no debe devolver ningún place cuyo `addressComponents.country != "AR"`.

**Fix robusto (1 semana)**
- Pre-geocoding de territorios al crearse (Google Geocoding API o servicio offline) → cache lat/lng/bbox/country en DB.
- Reject at input: si un territorio no geocodifica a un country único, forzar al usuario a elegir.
- Fuente-agnóstico: extraer `GeoConstraint` abstracción que funcione para Google Maps, Yelp, OSM.
- Telemetry: alert si ratio de leads en country != territory.country_code > 5%.

### Riesgo de repetirlo
**Alto** si no se agrega un test de regresión. Es el tipo de bug que volverá si un dev cambia el body de la request sin darse cuenta. **Propongo test integrador con mock de Places API.**

---

## 5. What Works Well (Preserve List)

Estas partes son reales, funcionales, no cosméticas:

- **`app/workflows/lead_pipeline.py`**: orquestador de LLM analysis honesto, contrato claro, manejo de degradación.
- **Accumulated context** (`app/services/pipeline/context_service.py`): acumula findings step-by-step con límites de tamaño (16KB run, 2KB step). Excelente diseño.
- **Dedup hash** (`app/services/leads/lead_service.py:16-24`): sha256 estricto sobre (name|city|website). Simple, previsible.
- **Janitor sweep core logic** (`app/workers/janitor.py:295-466`): detecta staleness en 4 capas (TaskRun 10min, PipelineRun 15min, orphan 30min, research 10min). Bien pensado.
- **Backpressure check** (`auto_pipeline_tasks.py:35`): queue_depth > 50 → skip. Previsto.
- **Idempotency guards** en enrich/score/analyze: `if lead.enriched_at is not None: skip`. Simples y efectivos.
- **Retry policy exponencial** (`pipeline_tasks.py:139`): `countdown=30 * (2**retries)`.
- **LOW_RESOURCE_MODE** (`celery_app.py:71-74`): concurrency=1, prefetch=1, colas merged. Sorprendentemente bien implementado.
- **Queue routing** (`celery_app.py:13-26`): separación por workload (enrichment, scoring, llm, reviewer, research). Buena higiene.
- **Structured logging + correlation_id** (`app/core/logging.py`, `bound_contextvars` en muchos workers). Debugging posible.
- **Scout agent real** (`app/agent/research_agent.py` + `app/agent/scout_tools.py`): loop agéntico real con Playwright, 6 tools, timeout 90s, max 10 loops. Es genuino.
- **Suppression at send time** (`app/services/outreach/outreach_service.py:44`): `is_suppressed(db, email=lead.email)` **sí se chequea antes de enviar** (contrario a lo que sugería una auditoría previa — verificado en grep).
- **DeadLetterTask table** (`app/models/dead_letter.py`): existe, se escribe. Falta el replay pero la estructura está.
- **Notifications system** (`app/services/notifications/notification_emitter.py`): capturas de eventos de negocio. Good audit foundation.

---

## 6. What Is Broken / Fragile / Fake

### Roto
- **Territory geo-anchoring**: el bug CABA→USA (ver §4). **Impact HIGH, Confidence HIGH.**
- **Follow-up chain**: no existe. Un lead CONTACTED que no responde queda en silencio — ninguna task lo levanta. **Impact HIGH.**
- **DLQ replay**: `DeadLetterTask` se escribe pero no hay proceso que la drene. Morgue pura. **Impact MED.**

### Frágil
- **`task_auto_process_new_leads` con `max_retries=0`** (`auto_pipeline_tasks.py:18`): si ese beat falla (ej: Redis hipo), no reintentará, pierdes 30min. **Impact MED.**
- **Research/Brief/ReplyDraft sin guard de idempotencia**: re-run crea duplicados. **Impact MED.**
- **Saturación de territorios unidireccional**: `is_saturated=True` nunca se limpia automáticamente. Si un territorio se "des-satura" (nuevos negocios meses después), requiere toque manual. **Impact MED.**
- **Replenish cap hardcoded 3 rondas** (`batch_pipeline.py`): si se agotan todos sin nuevos leads, **pipeline se para sin alerta agresiva**. **Impact MED.**
- **Soft timeout 300s global**: LLM calls largos (Scout research, review 27b) pueden rozarlo. Un 27b en CPU puede tardar más. **Impact MED.**
- **Ollama check health es solo HTTP ping** (`app/services/dashboard/health_service.py:58-71`): no valida que los modelos estén cargados.
- **Lock ausente en claim de lead**: dos workers podrían pasar la guard `if lead.enriched_at is None` simultáneamente. Baja probabilidad por queue routing, pero posible. **Impact LOW.**

### Engañoso (marketing > realidad)
- **"4 AI roles"**: son 2 agentes reales (Mote, Scout) + 2 invocaciones LLM stateless (Executor, Reviewer) sobre el mismo qwen3.5:9b. **Confidence HIGH** (verificado en llm/resolver.py + modelos idénticos).
- **"Reviewer quality gate"**: no bloquea pipeline. Escribe correcciones en `review_corrections`, alimenta prompts opcionales, no impide enviar. **Confidence HIGH.**
- **"AI team meetings"**: es un cron semanal (`weekly_tasks.py` Dom 20:00) que ejecuta `task_weekly_report` — una invocación LLM que sintetiza métricas. No hay consenso multi-agente, no hay deliberación, no hay voto. **Confidence HIGH.**
- **"Anti-zombie"**: 30% real (janitor detecta), 70% aspiracional (no remedia, solo marca/loguea/notifica). **Confidence HIGH.**
- **"58 agent tools"**: existen, son herramientas de Mote, pero **Mote no invoca a otros agentes**. Es conversacional con un humano. **Confidence HIGH.**

### Incompleto
- **No hay cost tracking real** (LLMInvocation sin tokens/USD). Imposible saber costo por lead convertido.
- **No hay event-store inmutable de transiciones** — history se reconstruye de timestamps. Debugging forense es dolor.
- **No hay on-startup recovery scan**: post-reinicio, nada verifica pipelines huérfanos hasta el próximo sweep (max 15min).
- **No hay alert channels externos**: notificaciones son DB-only; nadie recibe email/Slack/Telegram en stall.
- **Scoring sin feedback loop**: outcomes WON/LOST se guardan (`outcome_tracking_service.py`) pero no retroalimentan pesos de scoring.

### Técnicamente feo pero funcional
- **Deferred imports (~15 funciones)**: documentado en `AGENTS.md:61-64`. Smell de circular deps, pero controlado.
- **`janitor.py` de 466 líneas**: hace demasiadas cosas (sweep + orphan + zombie leads + stuck research + batch reviews + notifications). Scope creep clásico, pero todo útil.
- **Prompts de 900+ líneas total, 308 solo en review.py**: frágil pero versionado en git.
- **`STEP_CHAIN` duplicado en `janitor.py:42-53` y `api/v1/pipelines.py` (resume endpoint)**: single source of truth violado.

---

## 7. Autonomy Scorecard

| Dimensión | Score (1-10) | Razón breve |
|---|---|---|
| Startup | 7 | Arranca solo con config; depende de API keys + territorios humanos. |
| Continuous operation | 6 | Corre horas bien; se para al agotar territorios o al saturar. |
| Self-replenishment | 4 | Solo cron Mon/Thu; no auto-disparado por falta de leads fuera de ventana. |
| Territory expansion | 3 | `growth/adjacency.py` tiene lógica de sugerencias pero requiere approval humano. |
| Failure recovery | 6 | Janitor cubre 30-60% de casos; DLQ no drena; on-startup scan ausente. |
| Resume/restart | 7 | `task_acks_late` + manual resume API es correcto. Falta recovery automático post-crash. |
| Human independence | 4 | Drafts requieren approval (por diseño), outcomes no retroalimentan. |
| Observability | 6 | Logs sólidos + correlation_id. Faltan alerts externos y event-store. |
| Anti-zombie | 4 | Detecta, notifica, **no remedia**. 70% teatro. |
| Decision quality | 5 | Scoring estático, sin feedback loop de outcomes. |
| Lead quality | 5 | Volumen OK; filtros geo/niche ausentes; sin MX/phone validation. |
| Geo reliability | 2 | Bug CABA→USA = confianza quebrada. Hasta fix, no usar fuera de US. |
| Strategic adaptability | 3 | `batch_review_service` propone ajustes, pero humano aprueba. No aprende. |

**Promedio ponderado estimado: 4.6 / 10.** No es "automático"; es "mayormente automatizado con puntos humanos específicos". Lo cual **está bien** para lead gen B2B — pero vender la imagen de "autónomo de verdad" sería falso.

---

## 8. AI Meetings Verdict

**Respuesta brutal: HOY ES TEATRO. En 3-6 meses con fixes, puede ser útil pero como *report + policy engine*, no como *meeting multiagente*.**

### Análisis

La idea: "Las IAs se juntan cada N leads para revisar performance, ajustar territorios/fuentes/scoring".

**Qué pasa en realidad hoy** (`app/services/pipeline/batch_review_service.py`, `app/workers/weekly_tasks.py`):
- Cron domingo 20:00 ejecuta `task_weekly_report` → una invocación LLM que sintetiza métricas de la semana (conversión, territorios, correcciones más frecuentes).
- Brief se inyecta al system prompt de Mote.
- Cero consenso, cero voto, cero agentes deliberando.

### ¿Tiene sentido implementar "meetings" de verdad?

**No todavía. Acá está por qué:**

1. **Datos mínimos para que no sea teatro**:
   - ≥500 leads con outcome final (WON/LOST/NO_REPLY_30D) en ≥3 territorios distintos y ≥2 nichos.
   - Métricas de respuesta (reply rate, meeting rate, close rate) por feature del lead.
   - Costo por lead (tokens, Playwright minutos) — **HOY NO EXISTE**.

   Sin esto, un "meeting" de agentes es un LLM especulando con muestra insuficiente. Eso genera **recomendaciones con varianza alta = ajustes arbitrarios = daño al pipeline estable**.

2. **Decisiones reales que podría tomar** (en orden de riesgo ascendente):
   - Seguro: "sugerir ajuste de peso en signals A/B con evidencia".
   - Seguro: "recomendar pausar territorio X por bajo ROI".
   - Peligroso: "auto-ajustar pesos de scoring". **No debería hacerlo sola.**
   - Muy peligroso: "expandir outreach a nuevo nicho sin aprobación". **NUNCA.**

3. **¿Meeting multiagente o report + policy engine?**
   - **Report + policy engine gana claramente hasta escala >10k leads/mes.** Por qué:
     - Un meeting multiagente sobre datos ralos produce ruido.
     - Un policy engine con reglas ("si conv_rate territorio < 0.5% en 200 leads → pause & alert") es determinista y auditable.
     - El "meeting" tiene valor real solo cuando hay patrones cruzados entre agentes (Mote: "clientes me dicen X", Scout: "veo Y en sites", Executor: "drafts Z convierten") — y eso requiere **agentes con memoria de experiencia**, que hoy NO EXISTE (no hay embedding store de conversaciones/outcomes).

4. **ROI real**:
   - Hoy: negativo (costo LLM weekly + review sin acción enforceable).
   - Post-cost-tracking + feedback loop: potencial medio. Mejor que el status quo.
   - Vs. simple A/B testing de prompts + scoring weights tuning semi-manual: **tuning manual gana por simplicidad** en esta escala.

### Conclusión
**"Todavía no. Y cuando lo implementes, empezá como report + policy engine con approval humano, no como meeting de agentes."**

Criterios de listos:
- [x] Accumulated context ✓ (ya está)
- [ ] Cost tracking per lead (tokens + USD)
- [ ] Outcome feedback loop wired to scoring
- [ ] Geo bug fixed (sin esto, datos contaminados)
- [ ] ≥500 leads con outcome final limpio
- [ ] Experience memory (embedding store) por agente — solo si se va a "meeting" de verdad

Cuando tengas los primeros 4: policy engine con recomendaciones auto-aplicables bajo threshold + approval manual por encima.
Cuando tengas los 6: podés considerar meeting real.

---

## 9. Top 10 Risks (ordenados por severidad)

1. **[CRÍTICO] Geo bug CABA→USA contamina DB + quema Places API budget + envía outreach a negocios equivocados.**
   - `google_maps_crawler.py:195-199` + ausencia de uso de `cities_ar.get_coords()` en crawler.
   - Impact: pérdida de confianza del operador + costo Google + riesgo reputacional en outreach a US desde identidad AR.

2. **[ALTO] Self-replenishment roto fuera de Mon/Thu 8am.**
   - Si domingo todos los territorios saturan, sistema duerme hasta lunes 8am. Días muertos.
   - `crawl_tasks.py:65-80` + beat schedule.

3. **[ALTO] DLQ se llena pero nunca drena.**
   - `DeadLetterTask` se escribe (`_helpers.py:72-91`), no se procesa. Trabajo perdido silenciosamente.

4. **[ALTO] No cost tracking → no kill-switch por budget.**
   - `LLMInvocation` sin tokens/USD. Un prompt fugitivo o loop de Scout puede quemar $ sin alerta.

5. **[ALTO] Scoring sin feedback loop = decay invisible.**
   - Si hoy convierte 5% y en 3 meses convierte 0.5%, sistema no se entera hasta que humano mira métricas.

6. **[MED-ALTO] Research/Brief/ReplyDraft sin idempotencia → duplicados en re-run.**
   - Costo LLM duplicado + DB ruido + confusión de operador viendo dos briefs para el mismo lead.

7. **[MED-ALTO] Follow-up chain ausente.**
   - Lead CONTACTED sin respuesta = lead muerto. Nadie sigue, nadie escala, nadie suppress.

8. **[MED] `task_auto_process_new_leads` con max_retries=0.**
   - Un hipo de Redis = 30min perdidos sin alerta.

9. **[MED] Saturación unidireccional de territorios.**
   - `is_saturated=True` sin auto-limpieza periódica = territorio muerto para siempre.

10. **[MED] On-startup recovery ausente.**
    - Post-crash: solo se espera al janitor (5-30min). En producción con reinicios frecuentes = gap.

---

## 10. Top 10 Next Moves (ordenados por impacto / costo)

1. **[1-2h] Fix crítico del geo bug**: agregar `regionCode="AR"` + `locationBias` usando `get_coords()` en `google_maps_crawler.py:195-199`. Post-filter por `formattedAddress` contiene "Argentina". **Cierra el 90% del leak.**

2. **[1d] Agregar idempotency guards a research/brief/reply**:
   - `task_research_lead`: skip si existe `LeadResearchReport` con status SUCCEEDED para este lead en últimas 24h.
   - `task_generate_brief`: skip si `CommercialBrief` existente.
   - `generate_reply_assistant_draft`: skip si draft pendiente para ese inbound.

3. **[1d] Auto-replenish fuera de cron**:
   - En `task_auto_process_new_leads`, si `leads=[]` AND territorios activos no-saturados → disparar `task_crawl_territory` para el próximo.
   - Respetar backpressure.

4. **[1d] DLQ replay task**:
   - Beat task cada 1h: levanta DLQ con `replayed_at IS NULL` antigüedad <24h, re-dispatcha.
   - Max 1 replay por entry; marcar `replayed_at` tras intento.

5. **[2d] Cost tracking per LLMInvocation**:
   - Agregar columnas `prompt_tokens`, `completion_tokens`, `usd_cost_estimated`.
   - Wrapper en `invoke_structured()` para medir.
   - Threshold alert en `OperationalSettings`.

6. **[2d] Follow-up chain básica**:
   - Nueva task `task_check_followup` (beat cada 6h): leads CONTACTED sin inbound_message en N días → generar ReplyAssistantDraft de follow-up o escalar a humano.
   - N configurable por `OperationalSettings.followup_days`.

7. **[1d] Retries sensatos en beat tasks**:
   - `task_auto_process_new_leads`, `task_sync_inbound_mail`, `task_growth_cycle`: `max_retries=2`, `retry_backoff=True`.

8. **[1d] Alert channels externos**:
   - Telegram/Slack webhook en `notification_emitter._emit()` para category=system severity=critical.
   - Dedup con `dedup_key`.

9. **[2-3d] Event-store de transiciones**:
   - Nueva tabla `lead_events` (lead_id, event_type, old_status, new_status, metadata, ts).
   - Hooks en servicios que cambian `lead.status` para escribir.
   - Habilita forense + analytics + ML futuro.

10. **[3d] Auto des-saturación de territorios**:
    - Beat mensual: `is_saturated=True` AND `last_crawled_at > 60d ago` → reset a False.
    - Opcional: manual flag "never auto-unsaturate".

**Nota**: estos 10 moves son ~3-4 semanas de un dev dedicado. Ninguno requiere rediseño. Todos son **seams existentes endurecidos**.

---

## 11. Final Verdict

**Estado actual real**: Scouter es un **B+ en ingeniería, C en auto-marketing**. Es un pipeline LLM funcional y bien trazado, con base sólida de datos (accumulated context, dedup estricto, janitor, idempotency parcial), pero **vende autonomía que no entrega del todo** y tiene **un bug crítico de territorios** que corroe la confianza del operador.

**Qué lo separa del siguiente nivel**:
- **Técnico (ship en 3-4 semanas)**: los 10 moves de §10. Especialmente el geo fix, cost tracking, self-replenish, follow-up chain, idempotency gaps.
- **Producto**: definir claramente qué es *outreach válido* (geo + niche fit real), qué es *calidad de lead* medida contra outcomes, y empezar a cerrar el feedback loop scoring ↔ outcomes.
- **Narrativa**: dejar de llamarle "Agent OS" si no hay meeting/consensus/learning real. Llamarle "LLM ops pipeline con 2 agentes + 2 invocaciones curadas" es honesto y sigue siendo impresionante.

**Qué requiere producto/negocio (no solo código)**:
- **Definir el ICP geográfico-nicho** con precisión — hoy todo territorio y todo nicho es igual de válido. Esa es una **decisión de negocio**, no de código.
- **Decidir umbrales económicos**: costo máximo por lead, conversion rate mínimo para mantener un territorio. Sin esto, el policy engine no tiene dónde apoyarse.
- **Elegir si el producto vende "autonomía" o "cockpit"**. El código actual es cockpit; el marketing es autonomía. **Mentira actual = deuda con el usuario final**.

**Recomendación final**:
- **No rediseñar. No frenar. No "confiarle operación real total" todavía.**
- **Endurecer quirúrgicamente** con los 10 moves (en orden, uno por PR, conventional commits).
- **Fix crítico del geo bug esta semana**. Todo lo demás puede esperar si tiene que esperar.
- **Congelar narrative de "Agent OS" hasta tener closed-loop learning**. Mientras tanto, "lead prospecting pipeline con orquestación LLM y 2 agentes especializados" es lo honesto y suficientemente vendible.

Si tengo que responder la pregunta operativa del operador — *"¿puedo dejarlo corriendo solo?"* — la respuesta honesta hoy es: **"Sí, por 2-3 días, vigilando territorios y DLQ. Después necesitás tocar algo."** En 4 semanas con los fixes: **"Sí, con checkpoint humano semanal"**. En 3-6 meses con feedback loop real: **"Sí, con revisión mensual"**. Nunca será "lo prendés y te olvidás un año" — y está bien que no lo sea.

---

### Scoring (1-10)

| Dimensión | Score | Nota |
|---|---|---|
| Structure | 7 | Modular monolith bien seam-eado; deferred imports son smell controlado. |
| Backend | 7 | Services cohesivos, workflows explícitos, routing de queues prolijo. |
| Frontend | 6 | No auditado en profundidad; design tokens + shadcn sólido, pero fuera del scope. |
| Pipelines | 6 | Chaining implícito funciona pero falta orquestador durable; follow-up ausente. |
| Data model | 7 | 28 modelos, dedup hash, notifications. Faltan event-store + cost columns. |
| Testing | 6 | 325 pytest con PostgreSQL testcontainers = buena base; cobertura de geo y DLQ ausente. |
| Docs | 8 | `AGENTS.md`, `docs/` canónico, ADRs. Mejor que promedio. Vende agentic OS que no está. |
| Maintainability | 7 | Structlog + conventional commits + seams = mantenible. |
| Correctness | 5 | Geo bug + idempotency gaps + scoring sin feedback. |
| AI slop | 4 | Alto en marketing ("Agent OS", "team meetings", "anti-zombie" como concepto). Bajo en código (prompts razonables, poca duplicación). |

**Score global: ~6.3 / 10**. Con los 10 moves: ~7.8. Con cost tracking + feedback loop + follow-up real: ~8.5.

---

*Fin del informe.*
