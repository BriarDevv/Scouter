# Scouter Audit -- Current State

**Fecha:** 2026-04-02 (auditoría inicial) · Actualizado: 2026-04-02 (post-implementación Phase 0–4)
**Branch:** `main`
**Metodologia:** Inspeccion de codigo real del repositorio. Contraste contra `docs/product/proposal.md` (vision objetivo).

---

## 1. Executive Summary

Scouter es un sistema de prospecting funcional y operativo con base tecnica solida. Tiene un pipeline completo de lead ingestion -> enrichment -> scoring -> LLM analysis -> draft generation -> outreach delivery -> inbound reply handling, con un dashboard Next.js maduro (ahora 15 paginas) y un agente conversacional (Hermes/Claw) con 55 herramientas.

**Post-implementacion Phase 0-4:** Se agregaron dossiers, Commercial Briefs, research pipeline, export (CSV/JSON/XLSX), runtime modes, Prometheus metrics, idempotency guards, y las paginas /dossiers y /briefs al dashboard. Se corrigieron bugs criticos de decrypt WA/TG y se hizo docker hardening.

**Estado general: GREEN-YELLOW.** La infra core funciona y los gaps criticos de seguridad y observabilidad fueron cerrados. La capa de inteligencia comercial (dossier, brief, research, export) ahora existe. Queda pendiente: demos (Phase 5, postergada), Playwright browser-based research (actualmente HTTP-only), y tests de integracion con Postgres real.

---

## 2. Current Product Reality

Scouter HOY es:

1. **Un crawler de Google Maps** que busca negocios por territorio/categoria (`app/crawlers/google_maps_crawler.py`)
2. **Un pipeline de enriquecimiento** que analiza websites, extrae emails, detecta senales (`app/services/enrichment_service.py`)
3. **Un scoring engine** basado en reglas (0-100) con senales, industria, completeness y Google Maps (`app/scoring/rules.py`)
4. **Un analizador LLM** que genera summary + quality assessment + angulo comercial sugerido (`app/llm/client.py:summarize_business, evaluate_lead_quality`)
5. **Un generador de drafts** de email y WhatsApp con validacion anti-fabricacion (`app/outreach/generator.py`)
6. **Un sistema de outreach** con SMTP send, deliveries tracking, approval workflow (`app/services/mail_service.py, outreach_service.py`)
7. **Un sistema de inbound mail** con sync IMAP, thread matching, clasificacion LLM, reply assistant (`app/services/inbound_mail_service.py`)
8. **Un reviewer LLM** (27B) que revisa leads, drafts y replies inbound (`app/services/review_service.py`)
9. **Un agente conversacional** (Hermes/Claw, 8B) con 48 tools, SSE streaming, soporte multi-canal web/telegram/whatsapp (`app/agent/`)
10. **Un dashboard** con panel operativo, leads, outreach, responses, performance, mapa, suppression, notifications, security, settings, activity (`dashboard/`)
11. **Notificaciones multi-canal** (web, WhatsApp, Telegram) con severity filtering (`app/services/notification_service.py`)
12. **Feature toggles** comprensivos con resolucion DB-over-env (`app/models/settings.py`)

**Lo que NO es todavia:** un sistema de investigacion con evidencia, un generador de dossiers, un evaluador de oportunidad comercial, un estimador de presupuesto, ni un generador de demos.

---

## 3. Current Technical Reality

### Backend Stack
- **Framework:** FastAPI + SQLAlchemy 2.x (sync) + Pydantic 2.x
- **Workers:** Celery 5.4 + Redis, 5 queues (enrichment, scoring, llm, reviewer, default)
- **DB:** PostgreSQL 16 (tests en SQLite)
- **LLM:** Ollama local, 4 roles (LEADER 4B, EXECUTOR 9B, REVIEWER 27B, AGENT 8B)
- **Infra:** Docker Compose (6 servicios: postgres, redis, api, worker, flower, dashboard)
- **Auth:** API key middleware con timing-safe comparison
- **Encryption:** Fernet para credenciales SMTP/IMAP/WA/TG

### Frontend Stack
- **Framework:** Next.js 16 App Router, React 19, TypeScript strict
- **UI:** Tailwind v4, shadcn/ui con base-ui, framer-motion, recharts, leaflet
- **API client:** 67 funciones centralizadas en `lib/api/client.ts`
- **Estado:** Context API (ChatPanelProvider), localStorage persistence
- **Real-time:** SSE streaming para chat, polling 3-4s para tasks/pipeline

### Metricas del Repo
- **Modelos:** 20 tablas SQLAlchemy
- **Servicios:** 28 servicios en `app/services/`
- **Endpoints:** ~80 endpoints en 17 routers
- **Agent tools:** 48 herramientas registradas
- **Migraciones:** 30 Alembic migrations
- **Tests:** 153 tests en 21 archivos
- **Dashboard pages:** 13 paginas funcionales
- **API client functions:** 67

---

## 4. What Already Exists

### EXISTE y funciona (VERDE)

| Capacidad | Archivos clave | Estado |
|-----------|---------------|--------|
| Google Maps crawler con 25 categorias | `app/crawlers/google_maps_crawler.py` | Funcional |
| Dedup SHA-256 (name+city+domain) con unique constraint | `app/services/lead_service.py:16-24`, `app/models/lead.py:82` | Solido |
| Enrichment (website analysis, email extraction, signal detection) | `app/services/enrichment_service.py` | Funcional |
| Score rules-based 0-100 | `app/scoring/rules.py` | Funcional, 4 dimensiones |
| LLM analysis (summary + quality + angle) via Qwen 9B | `app/llm/client.py:summarize_business, evaluate_lead_quality` | Funcional |
| Draft generation email + WhatsApp con validacion | `app/outreach/generator.py` | Funcional, anti-fabricacion |
| SMTP outreach con delivery tracking | `app/services/mail_service.py`, `app/models/outreach_delivery.py` | Funcional |
| WhatsApp outreach via Kapso | `app/services/kapso_service.py`, `app/services/outreach_service.py` | Funcional |
| Inbound mail sync + thread matching | `app/services/inbound_mail_service.py` | Funcional |
| Reply classification LLM | `app/services/reply_classification_service.py` | Funcional |
| Reply assistant (generate + review + send) | `app/services/reply_response_service.py`, `reply_draft_review_service.py`, `reply_send_service.py` | Funcional |
| Reviewer LLM 27B (leads, drafts, inbound) | `app/services/review_service.py` | Funcional |
| Agent Hermes/Claw con 48 tools + SSE streaming | `app/agent/core.py`, `app/agent/tools/` | Funcional |
| Multi-channel agent (web + telegram + whatsapp) | `app/agent/channel_router.py` | Funcional |
| Pipeline orquestado (enrich -> score -> analyze -> draft) | `app/workers/tasks.py` | Funcional, con retries |
| Batch pipeline + territory crawl | `app/api/v1/pipelines.py`, `app/api/v1/crawl.py` | Funcional |
| Task tracking con pipeline runs | `app/services/task_tracking_service.py` | Funcional |
| Janitor (stale task sweep cada 5min) | `app/workers/janitor.py` | Funcional |
| Notifications multi-canal con severity/category | `app/services/notification_service.py` | Funcional |
| Feature toggles (30+ campos) | `app/models/settings.py` | Comprensivos |
| Dashboard 13 paginas funcionales | `dashboard/app/` | Maduro |
| Mapa interactivo con Leaflet + territorios | `dashboard/app/map/page.tsx` | Funcional |
| Settings 11 tabs con test buttons | `dashboard/app/settings/page.tsx` | Funcional |
| Activity monitor real-time | `dashboard/app/activity/page.tsx` | Funcional |
| Health checks (DB, Redis, Ollama, Celery) | `app/services/health_service.py` | Funcional |
| Structured logging con sensitive key scrubbing | `app/core/logging.py` | Solido |
| Fernet encryption para credenciales | `app/core/crypto.py` | Funcional |
| Territory CRUD con analytics | `app/services/territory_service.py` | Funcional |
| Suppression list | `app/services/suppression_service.py` | Funcional |

### EXISTE pero incompleto (AMARILLO)

| Capacidad | Estado | Gap |
|-----------|--------|-----|
| Instagram scraper con Playwright | `app/services/instagram_scraper.py` | Solo extrae bio link, bloquea worker thread con sleep(2) |
| Scoring | `app/scoring/rules.py` | Es quality score, no opportunity score |
| LeadSignal model | `app/models/lead_signal.py` | 12 signal types pero sin confidence levels |
| LLM quality assessment | `app/llm/client.py:evaluate_lead_quality` | Clasifica high/medium/low pero sin budget tier ni contact recommendation |
| WA/TG credentials encryption | `app/services/whatsapp_service.py`, `telegram_service.py` | Encrypt on write pero **sin decrypt on read** |
| Tests | `tests/` | 153 tests pero gaps en workers, crawlers, crypto, enrichment |

---

## 5. What Is Missing

### Gap vs Vision: ordenado por impacto

| # | Capacidad de la vision | Existe? | Esfuerzo estimado | Prioridad |
|---|----------------------|---------|-------------------|-----------|
| 1 | **Lead Dossier / Research Report** (modelo `lead_research_report`, screenshots, evidencia) | NO | Alto | Phase 1 |
| 2 | **High Lead Commercial Brief** (budget_tier, opportunity_score, recommended_contact, should_call) | NO | Alto | Phase 2 |
| 3 | **Playwright research pipeline** (web investigation, screenshots, HTML snapshots, confidence signals) | PARCIAL (solo Instagram bio) | Alto | Phase 1 |
| 4 | **Confidence levels** (website_confidence, instagram_confidence, whatsapp_confidence) | NO | Medio | Phase 1 |
| 5 | **Budget estimation** (estimated_budget_min/max, budget_tier, estimated_scope) | NO | Medio | Phase 2 |
| 6 | **Contact method recommendation** (recommended_contact_method, should_call, call_reason) | NO | Medio | Phase 2 |
| 7 | **Export/Artifacts** (CSV/XLSX/JSON/ZIP) | NO | Medio | Phase 1 |
| 8 | **Runtime modes** (Safe/Assisted/Auto global) | NO (hay toggles individuales) | Medio | Phase 3 |
| 9 | **Demo generation pipeline** (templates + Claude Code + deploy) | NO | Muy alto | Phase 5 |
| 10 | **Cockpit dashboard layout** (panel derecho contextual, dossier/brief inline) | NO (dashboard actual es operativo) | Alto | Phase 4 |
| 11 | **Application metrics** (Prometheus/OpenTelemetry) | NO | Medio | Phase 0 |
| 12 | **Observabilidad de costos LLM** | NO | Bajo | Phase 0 |
| 13 | **Idempotency guards** en workers | NO | Medio | Phase 0 |
| 14 | **Integration tests** (Postgres real, no SQLite) | NO | Medio | Phase 0 |

---

## 6. Product / Code Mismatches

Contradicciones concretas entre `docs/product/proposal.md` y el codigo real:

### 6.1 "Hermes coordina investigacion con Playwright"
- **Vision (seccion 4):** "Playwright recolecta evidencia y senales publicas del negocio"
- **Realidad:** Playwright solo se usa en `instagram_scraper.py` para extraer bio links. No hay pipeline de investigacion web. No hay captura de screenshots. No hay HTML snapshots.

### 6.2 "Dossier estructurado"
- **Vision (seccion 4):** "Qwen 9B resume y estructura un dossier"
- **Realidad:** `evaluate_lead_quality` produce un summary + quality + angle en el campo `llm_summary` del Lead. No hay modelo `lead_research_report` ni tabla de dossiers.

### 6.3 "High Lead Commercial Brief con budget tier"
- **Vision (seccion 5):** Modelo completo con budget_tier, estimated_budget_min/max, opportunity_score, recommended_contact_method, should_call, call_reason
- **Realidad:** Nada de esto existe. El unico scoring es rules-based (0-100) sin dimension comercial.

### 6.4 "Reviewer 27B valida el Commercial Brief"
- **Vision (seccion 4):** "Reviewer 27B revisa el dossier y define la estrategia comercial"
- **Realidad:** Reviewer existe y funciona para leads, drafts y replies inbound. **No revisa briefs ni dossiers** porque no existen.

### 6.5 "Export para leads HIGH"
- **Vision (seccion 11):** "CSV/XLSX para analisis, JSON para agentes, artifacts ZIP para leads HIGH"
- **Realidad:** Zero export functionality en todo el sistema.

### 6.6 "Dashboard como AI cockpit"
- **Vision (seccion 9):** Navegacion con Inbox, Dossiers, Commercial Briefs, Demos, Campaigns, Artifacts, Runtime
- **Realidad:** Navegacion con Hermes, Panel, Leads, Outreach, Respuestas, Rendimiento, Mapa, Supresion. No hay Dossiers, Briefs, Demos, Campaigns, Artifacts ni Runtime pages.

### 6.7 "Claude Code como worker premium"
- **Vision (seccion 7):** "Claude Code produce demos, adapta plantillas, genera artifacts tecnicos"
- **Realidad:** Claude Code no esta integrado al sistema. Toda la LLM execution es via Ollama local.

### 6.8 "Runtime modes Safe/Assisted/Auto"
- **Vision (seccion 9):** Modos globales con toggles por modulo (scraper, research, review, demo, send)
- **Realidad:** Hay toggles individuales por feature (mail, WA, TG, reply assistant, reviewer, etc.) pero no hay concepto de modo global.

---

## 7. Technical Debt

### RED -- Critico

| Item | Archivo | Impacto |
|------|---------|---------|
| WA/TG credentials encrypt sin decrypt on read | `app/services/whatsapp_service.py`, `telegram_service.py` | Credenciales cifradas se pasan verbatim a APIs externas = auth failures silenciosos |
| 4 findings de seguridad abiertos (PI-6/7/8, CC-7, CC-8) | `docs/operations/security-backlog.md` | Prompt injection en LLM, re-send sin limite, subject-based fallback matching |

### YELLOW -- Necesita atencion

| Item | Archivo | Impacto |
|------|---------|---------|
| Zero application metrics | Todo el sistema | No hay visibilidad de request duration, error rates, queue depth |
| Tasks no idempotentes con acks_late=True | `app/workers/tasks.py`, `celery_app.py:20` | Enrich/draft duplicados si worker crashea post-proceso pre-ack |
| Tests en SQLite vs Postgres en prod | `tests/conftest.py:19-21` | Divergencia en tipos, constraints, JSON ops |
| Sin tests para workers, crawlers, crypto, enrichment | `tests/` | 4 dominios criticos sin cobertura |
| API port en 0.0.0.0 | `docker-compose.yml:33` | Exposicion innecesaria en hosts con IP publica |
| Sin .dockerignore | Proyecto root | .env, .git, tests pueden filtrarse al build context |
| Instagram scraper bloquea worker thread | `app/services/instagram_scraper.py:58` | `time.sleep(2)` sincrono en worker Celery |
| Fetch ilimitado de leads en mapa | `dashboard/lib/api/client.ts:611-627` | `getLeadsWithCoords()` pagina todo = memory bomb en DB grande |
| Telegram alert settings reusa config de WhatsApp | `app/services/notification_service.py:287-288` | No se puede configurar TG independientemente |
| Docstring stale "plaintext" en mail_credentials | `app/models/mail_credentials.py:4` | Confuso, encryption ya fue agregada |

### GREEN -- Deuda minima

- Zero TODOs/FIXMEs/HACKs en el codigo
- Dependencies actualizadas (FastAPI 0.115+, Next.js 16, React 19, SQLAlchemy 2+)
- Session pool bien configurado (20+30, pre_ping, recycle)

---

## 8. Reliability Risks

| Riesgo | Severidad | Archivo | Mitigacion actual |
|--------|-----------|---------|-------------------|
| Worker crash post-proceso = task duplicada | MEDIO | `celery_app.py:20` | IntegrityError catch en task_tracking, partial unique en deliveries |
| Janitor marca failed tareas de >10min | BAJO | `janitor.py:14-55` | Podria matar tareas LLM legitimamente lentas (reviewer timeout 360s < 600s sweep) |
| No health check en containers api/worker/dashboard | MEDIO | `docker-compose.yml` | Solo dependen de DB/Redis healthy |
| Ollama down = pipeline se bloquea | MEDIO | Health check existe | Retries con backoff, pero sin circuit breaker |
| Single worker process = bottleneck | MEDIO | `docker-compose.yml:58-72` | Un solo `celery worker` con todas las colas |
| Cross-channel conversation sharing | BAJO | `channel_router.py:57-63` | Multiples usuarios TG/WA comparten misma conversacion |

---

## 9. UX / Dashboard Gaps

| Gap | Detalle | Impacto |
|-----|---------|---------|
| No hay vista de lead dossier | Dashboard muestra data plana del lead, no un dossier estructurado | No se puede evaluar un lead de un vistazo |
| No hay Commercial Brief view | No existe concepto de brief en el frontend | No hay lectura comercial previa al contacto |
| No hay exports | Ni CSV, ni XLSX, ni JSON, ni ZIP | Datos atrapados en el sistema |
| Actions desconectadas en leads table | Dropdown "Pipeline"/"Draft"/"Suprimir" no tienen onClick | UI promete mas de lo que hace |
| "Nuevo Lead" deshabilitado | `leads/page.tsx:33-40` con tooltip "Proximamente" | No se puede agregar leads manualmente desde UI |
| No hay panel contextual derecho | Vision describe panel derecho con score+brief+draft+demo | Dashboard actual es layout clasico sin contexto lateral |
| No hay Runtime view | Vision describe pagina de modos operativos | Solo hay toggles dispersos en Settings |
| 11 API client functions sin uso | `client.ts` | Dead code que confunde |
| Rendimiento no tiene data real | Performance page calcula insights client-side | Sin backend dedicado para analytics avanzados |

---

## 10. AI / Multi-Agent Gaps

| Gap | Vision | Realidad | Impacto |
|-----|--------|----------|---------|
| No hay research pipeline | Playwright investiga web, screenshots, evidencia | Solo Instagram bio scraper | Sin evidencia para decisiones comerciales |
| No hay dossier generation | Qwen 9B estructura dossier completo | `evaluate_lead_quality` genera summary basico | Sin lectura profunda del negocio |
| No hay opportunity scoring | opportunity_score 0-100 basado en senales de negocio | quality score basado en senales tecnicas | Score no refleja oportunidad comercial |
| No hay budget estimation | budget_tier + estimated_budget_min/max | Nada | No hay priorizacion por valor |
| No hay contact recommendation | recommended_contact_method + should_call + call_reason | Nada | Draft sin criterio de canal |
| No hay draft condicionado por brief | Drafts mejorados por investigacion real | Drafts basados en data de enrichment basica | Outreach generico |
| Claude Code no integrado | Worker premium para demos y artifacts | Ollama-only | Sin capacidad de generacion avanzada |
| Agent sin memoria persistente | Hermes deberia leer contexto historico | Cada conversacion empieza de cero | Sin continuidad operativa |
| No hay escalation logic | HIGH leads disparan research + review premium | Pipeline trata todos los leads igual (solo filtra high para draft) | Sin lane premium |

---

## 11. Data / Export / Artifact Gaps

| Gap | Detalle |
|-----|---------|
| Zero export capability | No hay endpoints ni UI para exportar nada |
| No hay modelo de artifact | No existe concepto de artifact ligado a lead |
| No hay screenshot storage | No hay modelo ni storage para capturas de Playwright |
| No hay dossier model | No hay tabla `lead_research_report` ni similar |
| No hay brief model | No hay tabla `commercial_brief` ni similar |
| No hay demo model | No hay tabla `demo_job` ni similar |
| No hay file storage abstraction | No hay S3/minio/local file service |
| Datos de lead limitados | Lead tiene 30+ campos pero sin research data, sin confidence signals, sin budget data |

---

## 12. Prioritized Gap List

Ordenado por impacto operativo y factibilidad, no por "lo mas cool":

| # | Gap | Tipo | Esfuerzo | Impacto | Fase |
|---|-----|------|----------|---------|------|
| 1 | Fix WA/TG decrypt on read | Bug critico | 1h | Critico | 0 |
| 2 | Resolver security audit findings | Seguridad | 1-2d | Critico | 0 |
| 3 | Add .dockerignore + bind API port | Infra | 30min | Medio | 0 |
| 4 | Add container health checks | Infra | 1h | Medio | 0 |
| 5 | Add application metrics (Prometheus) | Observabilidad | 1-2d | Alto | 0 |
| 6 | Add idempotency guards en workers | Reliability | 1d | Alto | 0 |
| 7 | Export basic (CSV/JSON leads) | Feature | 1-2d | Alto | 1 |
| 8 | Lead dossier model + table | Data foundation | 2-3d | Alto | 1 |
| 9 | Confidence signals en LeadSignal | Data model | 1d | Medio | 1 |
| 10 | Playwright research worker (website investigation) | Feature | 3-5d | Alto | 1 |
| 11 | Screenshot capture + storage | Feature | 2-3d | Medio | 1 |
| 12 | Dossier view en lead detail | Frontend | 2d | Alto | 1 |
| 13 | Commercial Brief model + generation | Feature | 3-5d | Alto | 2 |
| 14 | Opportunity score (business-based) | Feature | 2-3d | Alto | 2 |
| 15 | Budget estimation (tier + range) | Feature | 2-3d | Alto | 2 |
| 16 | Contact recommendation engine | Feature | 2d | Alto | 2 |
| 17 | Draft condicionado por brief | Feature | 2d | Medio | 3 |
| 18 | Runtime modes (Safe/Assisted/Auto) | Feature | 2-3d | Medio | 3 |
| 19 | Cockpit layout (panel contextual) | Frontend | 5-7d | Medio | 4 |
| 20 | Demo pipeline (templates + deploy) | Feature | 10-15d | Medio | 5 |

---

## 13. Recommended Immediate Focus

### Semana 1: Estabilizar realidad (Phase 0)
1. **Fix WA/TG decrypt** -- agregar `decrypt_safe()` en read paths de `whatsapp_service.py` y `telegram_service.py`
2. **Resolver security findings** -- PI-6/7/8 (sanitizar data en prompts), CC-7 (rate limit re-send), CC-8 (mejorar thread matching)
3. **Docker hardening** -- .dockerignore, bind API a 127.0.0.1, health checks en api/worker/dashboard
4. **Prometheus basic** -- `prometheus-fastapi-instrumentator` + /metrics endpoint
5. **Idempotency** -- check lead status before enrich/score, check existing draft before generate

### Semana 2-3: Lead Dossier Foundation (Phase 1)
1. Modelo `LeadResearchReport` + migracion Alembic
2. Confidence signals (website_confidence, instagram_confidence, whatsapp_confidence)
3. Playwright research worker (investigar web, detectar senales, capturar screenshots)
4. File storage abstraction (local en dev, S3 en prod)
5. Export CSV/JSON basico
6. Dossier view en lead detail page

### Semana 4-5: Commercial Brief (Phase 2)
1. Modelo `CommercialBrief` + migracion
2. LLM prompt para generar brief desde dossier
3. Opportunity score (LLM-based, senales de negocio)
4. Budget estimation (tier + range, matriz de pricing por scope)
5. Contact recommendation (method + should_call + call_reason)
6. Brief view en lead detail page

---

## 14. Suggested Architecture Direction

### Principio: Layered enrichment, no rewrite

La arquitectura actual (Lead -> Enrichment -> Scoring -> Analysis -> Draft) es sana. La recomendacion es **agregar capas encima**, no reemplazar:

```
Lead (existing)
  -> Enrichment (existing, extend with confidence)
  -> Scoring (existing)
  -> Analysis (existing)
  -> Research (NEW: Playwright worker)
  -> Dossier (NEW: structured report from research + analysis)
  -> Commercial Brief (NEW: budget + opportunity + contact recommendation)
  -> Enhanced Draft (NEW: draft conditioned on brief)
  -> Review (existing, extend to cover brief)
```

### Modelos nuevos sugeridos

```
LeadResearchReport
  - lead_id (FK)
  - research_data (JSON: screenshots, urls, signals, html_meta)
  - website_confidence (enum: confirmed/probable/unknown/mismatch)
  - instagram_confidence (enum)
  - whatsapp_confidence (enum)
  - researcher_model
  - created_at

CommercialBrief
  - lead_id (FK)
  - research_report_id (FK, nullable)
  - opportunity_score (0-100)
  - budget_tier (enum: low/medium/high/premium)
  - estimated_budget_min (Float)
  - estimated_budget_max (Float)
  - estimated_scope (enum: landing/web/catalog/ecommerce/redesign/automation/branding)
  - recommended_contact_method (enum: whatsapp/email/call/demo_first/manual_review)
  - should_call (enum: yes/no/maybe)
  - call_reason (Text)
  - why_this_lead_matters (Text)
  - main_business_signals (JSON)
  - main_digital_gaps (JSON)
  - recommended_angle (Text)
  - demo_recommended (Bool)
  - contact_priority (enum: immediate/high/normal/low)
  - generator_model
  - reviewer_model (nullable)
  - reviewed_at (nullable)
  - created_at

Artifact
  - lead_id (FK)
  - artifact_type (enum: screenshot/dossier/brief/demo/export)
  - file_path (Text)
  - metadata (JSON)
  - created_at
```

### Pipeline extendido para HIGH leads

```
task_enrich_lead (existing)
  -> task_score_lead (existing)
  -> task_analyze_lead (existing)
  -> IF quality == HIGH:
       -> task_research_lead (NEW: Playwright)
       -> task_generate_dossier (NEW)
       -> task_generate_brief (NEW)
       -> task_review_brief (NEW: REVIEWER)
  -> task_generate_draft (existing, conditioned on brief if available)
```

### File storage

Agregar abstraccion simple:
- Dev: local filesystem (`./storage/artifacts/`)
- Prod: S3-compatible (minio en docker, S3 en AWS)
- Interface: `save_artifact(lead_id, artifact_type, data) -> path`

---

## 15. Open Questions / Hypotheses to Validate

### Preguntas abiertas

1. **Playwright en Celery worker?** -- Playwright necesita Chromium. Correr en el mismo worker Celery que procesa LLM puede ser problematico. Evaluar si conviene un worker separado con cola `research`.

2. **Pricing matrix source of truth?** -- La vision dice que el budget estimation necesita una "tabla interna de pricing" por tipo de proyecto. Quien la define? Hardcoded? Configurable desde Settings?

3. **Screenshot storage volume?** -- Si se capturan screenshots de websites para cada lead HIGH, el storage crece rapido. Cuanto retention? Compresion? Lazy loading?

4. **Claude Code integration path?** -- La vision menciona Claude Code como worker premium para demos. Cual es el path de integracion? API? Claude Code SDK? Solo para Fase 5 o antes?

5. **Multi-operator?** -- El channel router comparte conversaciones entre canales. Si hay mas de un operador usando TG/WA, se mezclan. Es aceptable para v2?

6. **LLM cost tracking?** -- Con el pipeline extendido para HIGH leads (research + dossier + brief + review), el costo en tokens sube. Hay budget de infra definido?

### Hipotesis a validar

- **H1:** El quality score actual (reglas) es suficiente para gatillar la lane HIGH. Si no, se necesita un pre-screen LLM adicional.
- **H2:** La tabla de pricing puede ser un JSON configurable en OperationalSettings sin necesidad de tabla separada.
- **H3:** Los leads que hoy se clasifican como HIGH via `llm_quality` coinciden con los que el equipo considera oportunidades reales.
- **H4:** Un Playwright worker separado en Docker con cola dedicada es mas limpio que embeber Playwright en el worker general.
- **H5:** El dashboard actual puede evolucionar al cockpit sin refactor mayor -- se necesitan 3-4 paginas nuevas y un panel contextual, no reescritura.
