# ClawScout — Informe de Implementacion Phase 0-4

**Fecha:** 2026-04-02
**Autor:** Claude Opus 4.6 (OMC autopilot)
**Branch:** `main`
**Commits:** `0f7e2b0..ad5bb70` (7 commits)

---

## 1. Resumen Ejecutivo

Se ejecuto el roadmap completo de Phase 0 a Phase 4 en una sola sesion. Phase 5 (Demo Infrastructure) quedo postergada por decision explicita.

El trabajo se dividio en 3 etapas paralelas: backend Phase 1, backend Phase 2, y frontend Phases 1-4. Phase 0 y Phase 3 se implementaron directamente. Todo fue verificado con 178 tests pasando y TypeScript compilando sin errores.

**Resultado:** ClawScout paso de ser un sistema de scraping + drafts a tener dossiers, commercial briefs, export, runtime modes, Prometheus metrics, y un dashboard con 15 paginas funcionales y 55 agent tools.

---

## 2. Lo Que Se Hizo

### Phase 0 — Stabilize Reality
**Commit:** `0f7e2b0` · 10 archivos

| Cambio | Archivo | Detalle |
|--------|---------|---------|
| Fix decrypt WA/TG | `app/services/whatsapp_service.py` | Agregado `decrypt_safe()` en `send_alert()` y `test_whatsapp()` — antes pasaba ciphertext a la API |
| Fix decrypt TG | `app/services/telegram_service.py` | Agregado `decrypt_safe()` en `send_message()` y `test_telegram()` — mismo bug |
| Docker hardening | `docker-compose.yml` | API port a `127.0.0.1:8000`, dashboard a `127.0.0.1:3000`, health checks en api/worker/dashboard |
| .dockerignore | `.dockerignore` | Excluye .env, .git, tests, node_modules, __pycache__, *.db, *.key |
| Prometheus metrics | `app/main.py` | `prometheus-fastapi-instrumentator` con `/metrics` endpoint |
| Idempotency guards | `app/workers/tasks.py` | task_enrich_lead: skip si enriched_at set. task_score_lead: skip si scored_at set. task_analyze_lead: skip si llm_summary set. task_generate_draft: skip si draft existente pending/approved |
| Docstring fix | `app/models/mail_credentials.py` | "plaintext" -> "encrypted via Fernet" |
| Dependencies | `pyproject.toml` | Agregado `prometheus-fastapi-instrumentator>=7.0.0`, `openpyxl>=3.1.0` |
| Tests | `tests/test_crypto.py` | 8 tests: encrypt/decrypt roundtrip, encrypt_if_needed, decrypt_safe, is_encrypted |
| Tests | `tests/test_idempotency.py` | 3 tests: enrich/score/analyze skip cuando ya procesados |

### Phase 1 — Lead Dossier Foundation
**Commit:** `f846a8a` · 15 archivos

| Cambio | Archivo | Detalle |
|--------|---------|---------|
| Modelo LeadResearchReport | `app/models/research_report.py` | UUID PK, FK lead (unique), status enum (pending/running/completed/failed), confidence levels (confirmed/probable/unknown/mismatch), website/instagram/whatsapp analysis, screenshots_json, detected_signals_json, html_metadata_json, business_description, researcher_model, research_duration_ms |
| Modelo Artifact | `app/models/artifact.py` | UUID PK, FK lead, artifact_type enum (screenshot/dossier_pdf/export/brief), file_path, file_size, metadata_json |
| LeadSignal extendido | `app/models/lead_signal.py` | Nuevos campos: `confidence` (Float 0-1), `source` (String: enrichment/research/manual) |
| Lead relationships | `app/models/lead.py` | Agregados: `research_reports`, `artifacts` relationships |
| Research service | `app/services/research_service.py` | `run_research()`: analiza website via httpx + BeautifulSoup, detecta WhatsApp references, extrae HTML metadata (title, description, og_tags), trackea senales con confidence levels |
| Storage service | `app/services/storage_service.py` | `save_file()`, `get_file()`, `delete_file()`, `get_absolute_path()` — local filesystem con estructura `storage/{lead_id}/{category}/` |
| Export service | `app/services/export_service.py` | `export_leads_csv()`, `export_leads_json()`, `export_leads_xlsx()` — via openpyxl |
| LLM prompts | `app/llm/prompts.py` | DOSSIER_SYSTEM + DOSSIER_DATA — genera dossier JSON con business_description, digital_maturity, key_findings, improvement_opportunities |
| LLM client | `app/llm/client.py` | `generate_dossier()` — llama Ollama con role EXECUTOR, fallback si falla |
| API endpoints | `app/api/v1/leads.py` | GET `/leads/export?format=csv\|json\|xlsx`, GET `/leads/{id}/research`, POST `/leads/{id}/research` |
| Celery task | `app/workers/tasks.py` | `task_research_lead` — queue "research", max_retries=1, soft_time_limit=120. Pipeline: HIGH leads auto-encolan research despues de analysis |
| Celery routing | `app/workers/celery_app.py` | Agregado routing `task_research_lead` -> queue "research" |
| Migration | `alembic/versions/a2b3c4d5e6f7_...py` | CREATE TABLE lead_research_reports, CREATE TABLE artifacts, ADD COLUMN lead_signals.confidence, ADD COLUMN lead_signals.source |
| Schema | `app/schemas/research.py` | ResearchReportResponse Pydantic schema |
| Tests | `tests/test_research.py` | 9 tests: modelo, research service (sin web, con web mock, not found, idempotency), export CSV/JSON, signal confidence/source |

### Phase 2 — High Lead Commercial Brief
**Commit:** `7f7c17b` · 10 archivos

| Cambio | Archivo | Detalle |
|--------|---------|---------|
| Modelo CommercialBrief | `app/models/commercial_brief.py` | UUID PK, FK lead (unique), FK research_report (nullable). 6 enums: BudgetTier (low/medium/high/premium), EstimatedScope (landing/institutional_web/catalog/ecommerce/redesign/automation/branding_web), ContactMethod (whatsapp/email/call/demo_first/manual_review), CallDecision (yes/no/maybe), ContactPriority (immediate/high/normal/low), BriefStatus (pending/generated/reviewed/failed). Campos: opportunity_score, budget_tier, estimated_budget_min/max, estimated_scope, recommended_contact_method, should_call, call_reason, why_this_lead_matters, main_business_signals (JSON), main_digital_gaps (JSON), recommended_angle, demo_recommended, contact_priority, generator/reviewer_model |
| Brief service | `app/services/brief_service.py` | `generate_brief()`: pricing matrix lookup, LLM call, budget tier inference, contact priority inference. `get_pricing_matrix()`: DB > default fallback. Helpers: `_safe_float()`, `_safe_enum()`, `_infer_budget_tier()`, `_infer_contact_priority()` |
| LLM prompts | `app/llm/prompts.py` | COMMERCIAL_BRIEF_SYSTEM + COMMERCIAL_BRIEF_DATA — genera JSON con opportunity_score, estimated_scope, contact method, should_call, signals, gaps |
| LLM client | `app/llm/client.py` | `generate_commercial_brief()` — role EXECUTOR, fallback con manual_review recommendation |
| API endpoints | `app/api/v1/briefs.py` | GET `/briefs/leads/{id}`, POST `/briefs/leads/{id}`, GET `/briefs/` (list con filtros budget_tier, contact_priority) |
| Router | `app/api/router.py` | Registrado briefs router |
| Enhanced drafts | `app/outreach/generator.py` | Si lead tiene CommercialBrief, pasa recommended_angle al prompt de draft generation |
| Celery task | `app/workers/brief_tasks.py` | `task_generate_brief` — queue "llm", max_retries=1, con task tracking |
| Migration | `alembic/versions/a2b3c4d5e6f8_...py` | CREATE TABLE commercial_briefs |
| Tests | `tests/test_brief.py` | 5 tests: modelo, API 404, list empty, pricing matrix, budget tier inference |

### Phase 3 — Outreach Intelligence
**Commit:** `b510d33` · 7 archivos

| Cambio | Archivo | Detalle |
|--------|---------|---------|
| Runtime modes | `app/models/settings.py` | Nuevos campos: `runtime_mode` (String, default "safe"), `pricing_matrix` (String nullable, JSON) |
| Runtime presets | `app/services/operational_settings_service.py` | `apply_runtime_mode()`: safe (todo manual), assisted (pipeline auto, send manual), auto (todo auto). Cada modo setea 5 toggles atomicamente. Agregados `runtime_mode` y `pricing_matrix` a allowed fields y response dict |
| Runtime API | `app/api/v1/settings.py` | POST `/settings/runtime-mode?mode=safe\|assisted\|auto` |
| Notifications | `app/services/notification_emitter.py` | `on_research_completed()`: notifica cuando dossier listo. `on_brief_generated()`: notifica cuando brief listo (severity HIGH si should_call=yes) |
| Agent tools | `app/agent/tools/research.py` | 5 tools nuevos: `get_lead_dossier`, `run_lead_research` (requires_confirmation), `get_commercial_brief`, `generate_commercial_brief` (requires_confirmation), `export_leads` |
| Tool registry | `app/agent/tools/__init__.py` | Importa nuevo modulo `research` |
| Test fix | `tests/test_agent_core.py` | Tool count actualizado de 50 a 55 |

### Phase 4 — Cockpit Dashboard
**Commit:** `fd3360c` · 8 archivos

| Cambio | Archivo | Detalle |
|--------|---------|---------|
| Pagina /dossiers | `dashboard/app/dossiers/page.tsx` | Lista leads HIGH quality como candidatos a dossier. Links a detalle del lead |
| Pagina /briefs | `dashboard/app/briefs/page.tsx` | Lista commercial briefs con budget tier badge, opportunity score, estimated scope, should_call indicator, contact priority, budget range |
| Lead detail redesign | `dashboard/app/leads/[id]/page.tsx` | +450 lineas. Nuevas secciones colapsables: "Dossier" (website/instagram/whatsapp confidence, signals, HTML metadata, business description, duration) y "Brief Comercial" (opportunity score, budget tier, scope, contact method, call indicator, signals, gaps, angle). Botones "Investigar" y "Generar Brief" con loading states |
| Export dropdown | `dashboard/app/leads/page.tsx` | Dropdown "Exportar" con opciones CSV/JSON/XLSX usando `getExportUrl()` |
| Runtime mode UI | `dashboard/components/dashboard/control-center.tsx` | Selector safe/assisted/auto con indicadores de color (verde/ambar/rojo) y toast feedback |
| Sidebar | `dashboard/components/layout/sidebar.tsx` | Agregados Dossiers (FileSearch icon) y Briefs (Briefcase icon) despues de Leads |
| Types | `dashboard/types/index.ts` | LeadResearchReport, CommercialBrief, RuntimeMode, ConfidenceLevel, ResearchStatus, BudgetTier, EstimatedScope, ContactMethod, CallDecision, ContactPriority, BriefStatus |
| API client | `dashboard/lib/api/client.ts` | `getLeadResearch()`, `runResearch()`, `getCommercialBrief()`, `generateBrief()`, `listBriefs()`, `getExportUrl()`, `setRuntimeMode()` |

### Commits adicionales

| Commit | Detalle |
|--------|---------|
| `8426d49` | docs: audit completo + roadmap con status de implementacion |
| `ad5bb70` | refactor: layout wrappers normalizados en 8 paginas del dashboard |

---

## 3. Metricas del Trabajo

| Metrica | Valor |
|---------|-------|
| Commits | 7 |
| Archivos creados | 22 |
| Archivos modificados | 28 |
| Total archivos tocados | 50 |
| Lineas agregadas | ~4,200 |
| Tests nuevos | 25 (crypto: 8, idempotency: 3, research: 9, brief: 5) |
| Tests totales | 178 (0 failures) |
| TypeScript | Compila sin errores |
| Nuevos modelos | 3 (LeadResearchReport, Artifact, CommercialBrief) |
| Nuevos servicios | 4 (research, storage, export, brief) |
| Nuevos endpoints | ~10 |
| Nuevos agent tools | 5 |
| Nuevas paginas dashboard | 2 (/dossiers, /briefs) |
| Migraciones Alembic | 2 |
| Dashboard paginas totales | 15 (antes 13) |
| Agent tools totales | 55 (antes 48+2=50) |

---

## 4. Lo Que Queda Por Hacer

### Prioridad ALTA — Deberia hacerse pronto

| Item | Detalle | Esfuerzo |
|------|---------|----------|
| **Security findings PI-6/7/8** | Sanitizar data externa antes de pasarla a LLM prompts (strip HTML tags peligrosos, limitar longitud). Los tags `<external_data>` existen pero el contenido dentro no se sanitiza | 1-2d |
| **Security finding CC-7** | Rate limit en re-send de drafts fallidos (max 3 intentos por draft, cooldown 5min) | 4h |
| **Security finding CC-8** | Mejorar thread matching — Message-ID match como primer criterio antes de subject fallback | 4h |
| **Playwright browser research** | Research actual usa httpx (HTTP-only). Para screenshots reales y analisis visual se necesita un worker separado con Chromium | 3-5d |
| **Alembic migration run** | Las 2 migraciones nuevas estan creadas pero no corridas contra Postgres real. Correr `alembic upgrade head` cuando se levante el stack | 5min |
| **Integration tests** | Tests corren en SQLite. JSON columns y UUID types pueden comportarse diferente en Postgres. Evaluar Testcontainers | 2-3d |

### Prioridad MEDIA — Mejoras importantes

| Item | Detalle | Esfuerzo |
|------|---------|----------|
| **Brief review por REVIEWER** | El task `task_generate_brief` genera el brief pero no lo pasa al REVIEWER 27B para validacion. Agregar `task_review_brief` encadenado | 1d |
| **Pipeline full integration** | Encadenar: analysis -> research -> dossier -> brief -> draft. Hoy research se encadena desde analysis, pero dossier y brief no se generan automaticamente en el pipeline | 1d |
| **Dossier LLM generation** | `generate_dossier()` existe en el LLM client pero no se llama automaticamente despues de research. Conectar en `task_research_lead` | 4h |
| **Notification emitters wiring** | `on_research_completed()` y `on_brief_generated()` estan definidos pero no se llaman desde los services. Agregar calls en research_service y brief_service | 2h |
| **Export avanzado** | Export XLSX con multiples sheets (Leads, Dossiers, Briefs). Export ZIP para leads HIGH con todos los artifacts | 1-2d |
| **Pricing matrix UI** | El campo `pricing_matrix` esta en settings pero no hay UI en el dashboard para editarlo | 4h |
| **Telegram alert settings independientes** | Actualmente reusa config de WhatsApp (severity/categories). Necesita campos propios | 2h |

### Prioridad BAJA — Nice to have

| Item | Detalle | Esfuerzo |
|------|---------|----------|
| **S3 storage backend** | Storage service esta preparado para local. Agregar boto3 provider para produccion | 1d |
| **Dashboard analytics para briefs** | Metricas de briefs generados, distribution de budget tiers, conversion rates por contact method | 2-3d |
| **Batch brief generation** | Endpoint para generar briefs para todos los leads HIGH de un territorio | 1d |
| **Agent memory persistente** | Hermes empieza cada conversacion de cero. Agregar contexto historico | 3-5d |
| **Dead code cleanup** | 11 API client functions definidas pero nunca usadas en el dashboard | 2h |

---

## 5. Lo Que Hay Que Revisar

### Revisar antes de poner en produccion

1. **Correr migraciones** — `alembic upgrade head` contra Postgres real. Verificar que las tablas se crean correctamente con los tipos esperados (UUID, JSON, Enum).

2. **Test manual de decrypt** — Configurar credenciales WA/TG reales, verificar que `test_whatsapp()` y `test_telegram()` funcionan con tokens encriptados.

3. **Test manual de research** — Correr `POST /leads/{id}/research` contra un lead con website real. Verificar que el reporte se genera con signals y metadata.

4. **Test manual de brief** — Correr `POST /briefs/leads/{id}` contra un lead HIGH con Ollama corriendo. Verificar que genera opportunity_score, budget_tier, contact recommendation.

5. **Test manual de export** — Descargar CSV, JSON, XLSX desde `/leads/export`. Verificar formato y contenido.

6. **Test manual de runtime modes** — Cambiar entre safe/assisted/auto desde el ControlCenter. Verificar que los toggles se actualizan atomicamente.

7. **Dashboard visual review** — Navegar /dossiers, /briefs, lead detail con dossier/brief sections. Verificar layout en dark mode.

8. **Prometheus metrics** — Verificar que `/metrics` devuelve metricas HTTP (request count, duration histogram).

9. **Health checks Docker** — Verificar que `docker-compose ps` muestra health status para api, worker, dashboard.

10. **Pipeline end-to-end** — Crear un lead, correr full pipeline, verificar que para HIGH leads se encola research automaticamente.

### Cosas que podrian fallar

| Riesgo | Probabilidad | Mitigacion |
|--------|-------------|------------|
| Migracion Alembic falla en Postgres por tipos JSON/Enum | Media | Revisar DDL generado, testear en staging |
| LLM brief generation inconsistente (budget tiers erraticos) | Alta | Pricing matrix como constraint, REVIEWER valida, human approval |
| Research timeout en websites lentos | Media | soft_time_limit=120s, max_retries=1 |
| SQLite test divergence con nuevos modelos JSON | Alta | Evaluar Testcontainers con Postgres real |
| Alembic migration chain rota | Baja | Las 2 migraciones chainean desde heads existentes. Verificar `alembic heads` |

---

## 6. Arquitectura Post-Implementacion

### Pipeline de Lead (actualizado)

```
Lead ingestion (Google Maps crawler)
  -> Dedup (SHA-256)
  -> Enrichment (httpx website analysis, email extraction, signals)
  -> Scoring (rules-based, 0-100)
  -> LLM Analysis (Qwen 9B: summary + quality evaluation)
  -> IF quality == HIGH:
       -> Research (httpx website deep analysis, signals, metadata)  [NEW]
       -> [TODO: Dossier generation via LLM]                         [PARTIAL]
       -> [TODO: Commercial Brief generation via LLM]                [PARTIAL]
       -> [TODO: Brief review via REVIEWER 27B]                      [TODO]
  -> Draft Generation (email + WhatsApp, conditioned on brief if exists)
  -> Human Approval -> Send
```

### Modelos de Datos (actualizado)

```
Lead (existente, extendido)
  ├── LeadSignal (existente, +confidence, +source)
  ├── LeadResearchReport (NUEVO: website/instagram/whatsapp analysis)
  ├── CommercialBrief (NUEVO: budget, opportunity, contact rec)
  ├── Artifact (NUEVO: file storage tracking)
  ├── OutreachDraft (existente)
  ├── OutreachDelivery (existente)
  ├── EmailThread (existente)
  ├── InboundMessage (existente)
  ├── ReplyAssistantDraft (existente)
  └── PipelineRun (existente)
```

### Dashboard (actualizado)

```
Sidebar:
  Hermes (chat)
  Panel (dashboard)
  Leads (tabla)
  Dossiers (NUEVO)
  Briefs (NUEVO)
  Outreach
  Respuestas
  Rendimiento
  Mapa
  Supresion
  ---
  Notificaciones
  Seguridad
  Settings
```

### Runtime Modes

| Modo | Drafts requieren aprobacion | Auto-classify inbound | Reply assistant | Reviewer | WA outreach |
|------|------|------|------|------|------|
| **Safe** | Si | No | No | No | No |
| **Assisted** | Si | Si | Si | Si | No |
| **Auto** | No | Si | Si | Si | Si |

---

## 7. Commits Detallados

```
ad5bb70 refactor: normalize page layout wrappers across dashboard pages
8426d49 docs: add audit and roadmap with Phase 0-4 implementation status
fd3360c feat: Phase 4 — cockpit dashboard
b510d33 feat: Phase 3 — outreach intelligence
7f7c17b feat: Phase 2 — high lead commercial brief
f846a8a feat: Phase 1 — lead dossier foundation
0f7e2b0 security: Phase 0 — stabilize reality
```

---

## 8. Archivos Creados

```
# Modelos
app/models/research_report.py
app/models/artifact.py
app/models/commercial_brief.py

# Servicios
app/services/research_service.py
app/services/storage_service.py
app/services/export_service.py
app/services/brief_service.py

# API
app/api/v1/briefs.py

# Schemas
app/schemas/research.py
app/schemas/brief.py

# Workers
app/workers/brief_tasks.py

# Agent tools
app/agent/tools/research.py

# Migraciones
alembic/versions/a2b3c4d5e6f7_add_research_report_artifact_signal_confidence.py
alembic/versions/a2b3c4d5e6f8_add_commercial_brief.py

# Dashboard
dashboard/app/dossiers/page.tsx
dashboard/app/briefs/page.tsx

# Tests
tests/test_crypto.py
tests/test_idempotency.py
tests/test_research.py
tests/test_brief.py

# Infra
.dockerignore

# Docs
docs/archive/audits/clawscout-audit-current-state.md
docs/archive/reports/implementation-report-2026-04-02.md
docs/archive/roadmaps/clawscout-next-phase-plan.md
```

---

## 9. Phase 5 — Demo Infrastructure (POSTERGADA)

No se implemento por decision explicita. Queda documentada en el roadmap. Prerequisitos para abordarla:

1. Phase 2 validada con datos reales (briefs utiles)
2. Dominio `demo.clawscout.ai` disponible
3. Decision sobre Claude Code SDK vs API vs subprocess
4. Decision sobre hosting (Vercel preview, Cloudflare Pages, self-hosted)
5. Template framework definido (plain HTML, Next.js static export)

No se recomienda invertir en demos hasta que los Commercial Briefs demuestren valor medible.
