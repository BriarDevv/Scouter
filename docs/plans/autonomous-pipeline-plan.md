# Plan: Pipeline Autónomo de Scouter

**Fecha:** 2026-04-13
**Source:** Auditoría HARD de pipeline (5 agentes Opus)
**Score actual de autonomía:** 3.2/10
**Score objetivo:** 8.5+ (autonomía operativa real)

## Visión

El operador inicia el pipeline una sola vez. El sistema crawlea, procesa, enriquece, scorea, investiga, genera drafts, envía, y sigue trabajando. Si se queda sin leads, reabastece. Si algo falla, se recupera. Si un container muere, revive. Si algo sale mal, alerta. No para hasta que el operador diga STOP.

## Estado Actual

El pipeline tiene todas las piezas pero están desconectadas:
- El crawl periódico (Lun+Jue 8am) crea leads pero nada los procesa automáticamente
- El modo `auto` aprueba y envía drafts sin humano, pero el pipeline requiere trigger manual
- La resiliencia de tasks es buena (retries, idempotencia, fallbacks) pero no hay re-queue de fallas ni alerting
- No hay Docker restart policies — un crash es permanente
- No hay detección de saturación de territorio ni expansión automática

## Etapas

---

### Etapa 1: "No se muere" — Resiliencia base

**Esfuerzo:** ~1 día | **Score:** 3.2 → 6.0

#### E1-1: Docker restart policies
- **Archivo:** `docker-compose.yml`
- **Cambio:** Agregar `restart: unless-stopped` a todos los servicios (postgres, redis, api, worker, worker-llm, flower, dashboard)
- **Por qué:** Sin esto, un OOM kill o segfault mata el servicio permanentemente
- **Riesgo:** Bajo — si un servicio tiene un crash loop, Docker lo reinicia cada vez. Monitorear con `docker compose logs`

#### E1-2: Auto-pipeline trigger en Celery Beat
- **Archivos:** `app/workers/celery_app.py`, nuevo `app/workers/auto_pipeline_tasks.py`
- **Cambio:** 
  - Crear task `task_auto_process_new_leads` que:
    1. Verifica `OperationalSettings.auto_pipeline_enabled` (nuevo campo, default False)
    2. Consulta leads con `status=new` y `created_at > 10min ago` (evita procesar leads recién creados que el operador quiere revisar)
    3. Para cada lead, despacha `task_full_pipeline.delay(lead_id)`
    4. Cap de N leads por ciclo (configurable, default 20) para evitar saturar queues
  - Agregar a `beat_schedule`: cada 30 minutos
- **Por qué:** Cierra el gap principal entre crawl y processing
- **Riesgo:** Medio — podría procesar leads que el operador quería revisar primero. Mitigado con el campo `auto_pipeline_enabled` (opt-in) y el delay de 10 minutos

#### E1-3: Alerting de fallas de pipeline
- **Archivos:** `app/workers/_helpers.py`, `app/workers/janitor.py`, `app/services/notifications/notification_emitter.py`
- **Cambio:**
  - En `_track_failure` (cuando un task agota max_retries): emitir notificación HIGH via `notification_emitter`
  - En janitor `sweep_stale_tasks` (cuando marca N+ tasks como failed en un ciclo): emitir notificación CRITICAL
  - Wire `on_repeated_failures` (actualmente código muerto en `notification_emitter.py:297`) a estos puntos
- **Por qué:** Sin alertas, las fallas son invisibles. El operador no sabe que algo murió.
- **Riesgo:** Bajo — son notificaciones, no cambian comportamiento

#### E1-4: Retry en crawl tasks
- **Archivo:** `app/workers/crawl_tasks.py`
- **Cambio:** Cambiar `max_retries=0` a `max_retries=1, default_retry_delay=60` en `task_crawl_territory` y `task_scheduled_crawl`
- **Por qué:** Un error transitorio de Google Maps API pierde todo el ciclo de crawl
- **Riesgo:** Bajo — un retry con 60s de delay es conservador

#### E1-5: Retry en clientes externos
- **Archivos:** `app/services/comms/kapso_service.py`, `app/crawlers/google_maps_crawler.py`
- **Cambio:** Agregar tenacity retry decorator (mismo patrón que `enrichment_service.py:21-26`):
  ```python
  @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=10),
         retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
  ```
- **Por qué:** Fallas transitorias de red son permanentes sin retry
- **Riesgo:** Bajo — 2 retries con backoff no estresa los APIs

#### E1-6: HTTP 5xx retry en LLM client
- **Archivo:** `app/llm/client.py`
- **Cambio:** Agregar `httpx.HTTPStatusError` al retry filter de `_chat_completion`, con guard que solo retrie 5xx (no 4xx)
- **Por qué:** Ollama devolviendo 500 (server overloaded) o 503 (model loading) es transitorio pero actualmente falla permanente
- **Riesgo:** Bajo

**Commits esperados:**
```
fix(docker): add restart policies to all compose services
feat(pipeline): add auto-pipeline trigger to Celery Beat schedule
feat(alerts): wire failure alerting into janitor and task tracker
fix(crawl): add retry logic to territory crawl tasks
fix(comms): add tenacity retry to Kapso and Google Maps clients
fix(llm): retry on HTTP 5xx from Ollama
```

---

### Etapa 2: "Se reabastece" — Supply chain de leads

**Esfuerzo:** ~2-3 días | **Score:** 6.0 → 7.5

#### E2-1: Inbound mail sync automático
- **Archivo:** `app/workers/celery_app.py`, nuevo `app/workers/inbox_tasks.py`
- **Cambio:**
  - Crear task `task_sync_inbound_mail` que ejecuta el sync IMAP
  - Agregar a `beat_schedule`: cada 15 minutos
  - Gate: solo corre si `MAIL_INBOUND_ENABLED=true`
- **Por qué:** Emails de clientes se acumulan sin leer hasta sync manual

#### E2-2: Modelo Territory con tracking de crawl
- **Archivos:** `app/models/territory.py`, nueva migración Alembic
- **Cambio:** Agregar campos:
  - `last_crawled_at: DateTime` — cuándo se crawleó por última vez
  - `last_dup_ratio: Float` — ratio de duplicados del último crawl
  - `crawl_count: Integer` — cuántas veces se crawleó
  - `is_saturated: Boolean` — marcado cuando dup_ratio > 0.8 por 2 crawls consecutivos
- **Por qué:** Sin estos datos, el sistema crawlea a ciegas

#### E2-3: Detección de saturación post-crawl
- **Archivo:** `app/workflows/territory_crawl.py`
- **Cambio:** Después de completar un crawl (línea ~247), calcular `dup_ratio = total_dup / max(total_found, 1)`. Actualizar `territory.last_crawled_at`, `territory.last_dup_ratio`, `territory.crawl_count`. Si `dup_ratio > 0.8` y el anterior también era > 0.8, marcar `is_saturated=True` y emitir notificación
- **Por qué:** El sistema necesita saber cuándo un territorio ya no rinde

#### E2-4: Cooling period en scheduled crawl
- **Archivo:** `app/workers/crawl_tasks.py`
- **Cambio:** En `task_scheduled_crawl`, filtrar territorios:
  ```python
  territories = db.query(Territory).filter(
      Territory.is_active == True,
      Territory.is_saturated == False,
      or_(Territory.last_crawled_at == None,
          Territory.last_crawled_at < datetime.utcnow() - timedelta(days=3))
  ).all()
  ```
- **Por qué:** Evita recrawlear territorios frescos o saturados

#### E2-5: Rotación inteligente en batch auto-crawl
- **Archivo:** `app/workflows/batch_pipeline.py`
- **Cambio:** Reemplazar `territories[0]` con:
  ```python
  territory = db.query(Territory).filter(
      Territory.is_active == True,
      Territory.is_saturated == False
  ).order_by(Territory.last_crawled_at.asc().nullsfirst()).first()
  ```
- **Por qué:** Siempre crawlear el territorio menos reciente en vez del primero por ID

#### E2-6: Wire status QUALIFIED para leads no-actionable
- **Archivos:** `app/workers/pipeline_tasks.py`, `app/workflows/batch_pipeline.py`, `app/workflows/outreach_draft_generation.py`
- **Cambio:** Cuando `task_generate_draft` devuelve `status=skipped` (calidad no-HIGH, sin email, o brief rechazado), setear `lead.status = LeadStatus.QUALIFIED` en vez de dejar en `SCORED`
- **Por qué:** Los leads non-actionable quedan en SCORED como un cementerio invisible. QUALIFIED los hace visibles y queryables

**Commits esperados:**
```
feat(inbox): add inbound mail sync to Celery Beat schedule
feat(territory): add saturation tracking fields to Territory model
feat(territory): detect and record crawl saturation ratios
feat(crawl): add cooling period to scheduled territory crawl
refactor(pipeline): rotate territories by least-recently-crawled
fix(lifecycle): wire QUALIFIED status for non-actionable analyzed leads
```

---

### Etapa 3: "Se recupera" — Self-healing

**Esfuerzo:** ~2-3 días | **Score:** 7.5 → 8.5

#### E3-1: Janitor re-queue de pipelines fallidos
- **Archivo:** `app/workers/janitor.py`, nueva columna `retry_count` en PipelineRun
- **Cambio:**
  - Después de marcar un PipelineRun como failed, verificar:
    - `retry_count < 2` (máximo 2 re-intentos automáticos)
    - Falla es retryable (timeout, LLM error — no validation error)
  - Si es retryable, despachar el siguiente step usando la misma lógica que el resume endpoint
  - Incrementar `retry_count`
- **Por qué:** Hoy el janitor es un coroner — detecta muertos pero no resucita
- **Riesgo:** Medio — sin cap de retries crearía loops infinitos. El `retry_count=2` lo limita

#### E3-2: Dead letter table
- **Archivos:** Nuevo modelo `app/models/dead_letter.py`, nueva migración, update a `_track_failure`
- **Cambio:**
  - Crear tabla `dead_letter_tasks` con: `task_name`, `lead_id`, `pipeline_run_id`, `step`, `error`, `payload` (JSON), `created_at`, `replayed_at`
  - Cuando un task agota max_retries, además de marcar failed, insertar en dead_letter
  - Endpoint `POST /api/v1/pipelines/dead-letter/replay/{id}` para replay manual
- **Por qué:** Tasks que mueren desaparecen. Con dead letter son queryables y replayables

#### E3-3: Lead-level zombie janitor
- **Archivo:** `app/workers/janitor.py`
- **Cambio:** Agregar sweep que busca leads stuck:
  - `ENRICHED` sin cambio por > 1 hora
  - `SCORED` sin pipeline_run por > 24 horas (excluyendo QUALIFIED)
  - `DRAFT_READY` con draft `PENDING_REVIEW` por > 48 horas
  - Para cada uno, emitir notificación y opcionalmente re-queue pipeline
- **Por qué:** El janitor actual solo mira tasks, no leads. Un lead puede morir en silencio

#### E3-4: Research report zombie sweep
- **Archivo:** `app/workers/janitor.py`
- **Cambio:** Agregar sweep de `LeadResearchReport.status == 'running'` por más de 10 minutos → marcar como `failed`
- **Por qué:** Reports stuck no son detectados por el janitor actual

#### E3-5: Chain scheduled crawl con batch pipeline
- **Archivo:** `app/workers/crawl_tasks.py`
- **Cambio:** En `task_scheduled_crawl`, después de que todos los territory crawls terminan, si `auto_pipeline_enabled`: despachar `task_batch_pipeline.delay()` con los leads recién creados
- **Por qué:** Conecta crawl → process inmediatamente, sin esperar el next auto-pipeline cycle
- **Alternativa:** Si E1-2 ya está implementado, el auto-pipeline trigger cada 30min cubre esto. Esta optimización reduce latencia de ~30min a ~0min

**Commits esperados:**
```
feat(janitor): add auto-resume for retryable failed pipelines
feat(pipeline): add dead letter table for exhausted tasks
feat(janitor): add lead-level zombie detection sweep
feat(janitor): add research report zombie sweep
feat(pipeline): chain scheduled crawl into batch pipeline dispatch
```

---

### Etapa 4: "Se ve" — Observability para autonomía

**Esfuerzo:** ~2-3 días | **Score:** 8.5 → 9.0

#### E4-1: Celery task metrics en Prometheus
- **Archivos:** Nuevo `app/workers/metrics.py`, update `celery_app.py`
- **Cambio:** Usar Celery signals (`task_success`, `task_failure`, `task_retry`) para exponer métricas:
  - `scouter_task_total{task_name, status}` — counter de tasks completadas/fallidas
  - `scouter_task_duration_seconds{task_name}` — histogram de duración
  - `scouter_queue_depth{queue_name}` — gauge de profundidad de cola (via Redis LLEN)
- **Por qué:** Prometheus solo tiene HTTP metrics. Sin task metrics no se ven bottlenecks ni failures

#### E4-2: Pipeline throughput dashboard
- **Archivos:** `app/services/dashboard/dashboard_service.py`, dashboard frontend
- **Cambio:** Agregar métricas de pipeline:
  - Leads procesados/hora (últimas 24h)
  - Lead inventory por status (how many NEW, ENRICHED, SCORED, etc.)
  - Pipeline failure rate (últimas 24h)
  - Territory yield (leads created vs duplicates, por territorio)
- **Por qué:** El operador necesita ver de un vistazo si el pipeline está sano o muriéndose

#### E4-3: Alertas de pipeline inactivo
- **Archivo:** `app/workers/janitor.py`
- **Cambio:** Si en los últimos 60 minutos no se completó ningún PipelineRun y hay leads `status=new` → emitir notificación "Pipeline seems inactive"
- **Por qué:** El pipeline puede estar quieto sin que nadie se dé cuenta

#### E4-4: Señales de agotamiento de territorio
- **Archivo:** `app/workers/crawl_tasks.py`
- **Cambio:** Después de un scheduled crawl, si TODOS los territorios activos están saturados (`is_saturated=True`) → emitir notificación CRITICAL "All territories saturated — consider expanding"
- **Por qué:** Si no hay territorios frescos, el supply chain se seca

**Commits esperados:**
```
feat(metrics): add Celery task metrics to Prometheus
feat(dashboard): add pipeline throughput and lead inventory metrics
feat(janitor): add pipeline-inactive detection and alert
feat(crawl): alert when all territories are saturated
```

---

### Etapa 5: "Es inteligente" — Autonomía avanzada

**Esfuerzo:** ~2-4 semanas | **Score:** 9.0 → 9.5+

#### E5-1: Auto-reply draft generation
- Después de clasificar un inbound message en modo auto, si el label es `interested`/`asked_for_quote`/`asked_for_meeting`, auto-generar reply draft

#### E5-2: Post-CONTACTED automation
- Cuando inbound mail match detecta un reply a un lead CONTACTED, auto-avanzar a REPLIED
- Wire email open tracking → auto-avanzar a OPENED

#### E5-3: Territory expansion con geocoding
- Agregar geocoding a ciudades (lat/lng via Google Geocoding)
- Función de adjacencia que sugiere ciudades cercanas
- Cuando saturación detectada, auto-expandir con ciudades adyacentes (gate: requiere operator approval)

#### E5-4: API budget/quota awareness
- Redis counter de API calls por día
- `GOOGLE_MAPS_DAILY_QUOTA` setting
- Circuit breaker cuando se alcanza el límite

#### E5-5: Backpressure-aware dispatching
- Auto-pipeline chequea queue depth antes de despachar
- Si `llm` queue > 50 pending: skip cycle
- Previene sobrecarga en Ollama

**Commits:** TBD — depende de lo que se priorice

---

## Score Proyectado por Etapa

| Etapa | Score | Qué cambia |
|-------|-------|------------|
| Actual | 3.2 | Batch manual, sin alertas, sin restart |
| Etapa 1 | ~6.0 | Auto-trigger, restart policies, alertas, retry |
| Etapa 2 | ~7.5 | Self-replenishment, saturación, mail sync, status fix |
| Etapa 3 | ~8.5 | Self-healing, dead letter, zombie detection |
| Etapa 4 | ~9.0 | Observability completa, métricas, pipeline-inactive alert |
| Etapa 5 | ~9.5 | Auto-reply, territory expansion, budget awareness |

## Dependencias entre Etapas

```
Etapa 1 → Etapa 2 (E2-4 cooling period necesita E2-2 territory fields)
Etapa 1 → Etapa 3 (E3-1 re-queue necesita E1-3 alerting)
Etapa 2 → Etapa 4 (E4-4 saturación alert necesita E2-3 saturation detection)
Etapas 1-3 → Etapa 5 (autonomía avanzada depende de base estable)
```

Dentro de cada etapa, los items son independientes y paralelizables.
