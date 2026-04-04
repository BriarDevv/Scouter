# Scouter -- Next Phase Plan

**Fecha:** 2026-04-02
**Basado en:** Auditoria real del repositorio (`docs/archive/audits/scouter-audit-current-state.md`)
**Vision objetivo:** `docs/product/proposal.md`
**Estado de implementacion:** Phase 0-4 DONE (2026-04-02). Phase 5 POSTERGADA.

### Implementation Summary
| Phase | Status | Commit |
|-------|--------|--------|
| Phase 0 — Stabilize Reality | **DONE** | `0f7e2b0` |
| Phase 1 — Lead Dossier Foundation | **DONE** | `e4c274f` |
| Phase 2 — High Lead Commercial Brief | **DONE** | `e4c274f` |
| Phase 3 — Outreach Intelligence | **DONE** | `e4c274f` |
| Phase 4 — Cockpit Dashboard | **DONE** | `e4c274f` |
| Phase 5 — Demo Infrastructure | **POSTERGADA** | — |

---

## Phase 0 -- Stabilize Reality

**Objetivo:** Cerrar bugs criticos, hardening de infra, baseline de observabilidad.
**Duracion estimada:** 1 semana
**Criterio:** Zero RED items en la auditoria. Metricas basicas visibles.

### 0.1 Fix WA/TG credential decrypt (1h)
- Agregar `decrypt_safe()` en read paths de `whatsapp_service.py` y `telegram_service.py`
- Replicar patron de `mail_credentials_service.py:132,144`
- **Archivos:** `app/services/whatsapp_service.py`, `app/services/telegram_service.py`
- **Test:** Verificar que `test_whatsapp()` y `test_telegram()` funcionan con credenciales reales

### 0.2 Security audit findings (1-2d)
- **PI-6/7/8:** Agregar sanitizacion de `<external_data>` content antes de pasarlo al LLM -- strip HTML tags peligrosos, limitar longitud
- **CC-7:** Rate limit en re-send de drafts fallidos (max 3 intentos por draft, cooldown 5min)
- **CC-8:** Mejorar thread matching -- agregar Message-ID match como primer criterio antes de subject fallback
- **Archivos:** `app/llm/prompts.py`, `app/services/outreach_service.py`, `app/services/inbound_mail_service.py`
- Actualizar `docs/operations/security-backlog.md` marcando SEC-9 como resuelto

### 0.3 Docker hardening (30min)
- Crear `.dockerignore`: `.env`, `.git/`, `node_modules/`, `*.db`, `*.key`, `*.pem`, `tests/`, `__pycache__/`
- Cambiar `docker-compose.yml:33` de `"8000:8000"` a `"127.0.0.1:8000:8000"`
- Agregar `healthcheck` en containers api, worker, dashboard

### 0.4 Application metrics (1-2d)
- Instalar `prometheus-fastapi-instrumentator`
- Agregar `/metrics` endpoint en `app/main.py`
- Metricas custom: `scouter_tasks_total` (counter por tipo+status), `scouter_llm_calls_total` (counter por role+model), `scouter_llm_duration_seconds` (histogram)
- **Archivos:** `app/main.py`, `app/llm/client.py`, `app/workers/tasks.py`, `pyproject.toml`

### 0.5 Worker idempotency (1d)
- `task_enrich_lead`: skip si lead.enriched_at != None y no force=True
- `task_score_lead`: skip si lead.scored_at != None y no force=True
- `task_generate_draft`: skip si ya existe draft pending_review/approved para el lead
- `task_analyze_lead`: skip si lead.llm_summary != None y no force=True
- **Archivo:** `app/workers/tasks.py`

### 0.6 Test gaps criticos (1d)
- Tests para `encrypt_if_needed()` / `decrypt_safe()` round-trip
- Tests para `task_enrich_lead` / `task_score_lead` (mock LLM + DB)
- Test de idempotency guards

---

## Phase 1 -- Lead Dossier Foundation

**Objetivo:** Agregar capa de investigacion + dossier estructurado para leads HIGH.
**Duracion estimada:** 2-3 semanas
**Criterio:** Lead HIGH tiene dossier con evidencia. Export basico funciona.

### 1.1 Data models (2-3d)
- **Nuevo modelo `LeadResearchReport`:**
  - lead_id (FK unique), status (enum: pending/running/completed/failed)
  - website_exists (Bool), website_url_verified (Text), website_confidence (enum: confirmed/probable/unknown/mismatch)
  - instagram_exists (Bool), instagram_url_verified (Text), instagram_confidence (enum)
  - whatsapp_detected (Bool), whatsapp_confidence (enum)
  - screenshots_json (JSON: list of {url, path, captured_at})
  - detected_signals_json (JSON: list of {type, detail, confidence})
  - html_metadata_json (JSON: {title, description, og_tags, tech_stack})
  - business_description (Text, LLM-generated summary from evidence)
  - researcher_model (String), research_duration_ms (Int)
  - created_at, updated_at
- **Extender `LeadSignal`:** agregar `confidence` (Float 0-1) y `source` (enum: enrichment/research/manual)
- **Nuevo modelo `Artifact`:**
  - lead_id (FK), artifact_type (enum: screenshot/dossier_pdf/export/brief), file_path (Text), file_size (Int), metadata_json (JSON), created_at
- Alembic migration
- **Archivos:** `app/models/research_report.py`, `app/models/artifact.py`, `app/models/lead_signal.py`, `app/models/__init__.py`

### 1.2 File storage abstraction (1d)
- `app/services/storage_service.py`: `save_file(lead_id, category, filename, data) -> path`, `get_file(path) -> bytes`, `delete_file(path)`
- Dev: `./storage/` local
- Prod: S3-compatible via `boto3` (configurar con `STORAGE_BACKEND=local|s3`, `S3_BUCKET`, `S3_ENDPOINT`)
- **Archivos:** `app/services/storage_service.py`, `app/core/config.py`

### 1.3 Playwright research worker (3-5d)
- **Nueva cola Celery:** `research`
- **Docker:** Worker separado con Playwright + Chromium (no contaminar worker general)
- **Task `task_research_lead`:**
  1. Abrir website del lead (si existe)
  2. Capturar screenshot full-page
  3. Extraer metadata HTML (title, description, og tags, tech stack indicators)
  4. Detectar senales: SSL, mobile-friendly, load time, CTA, WhatsApp widget, contact forms
  5. Si tiene Instagram: verificar perfil, extraer bio, link, follower signals
  6. Guardar screenshots via storage service
  7. Crear/actualizar `LeadResearchReport`
- Soft time limit: 120s. Max retries: 1.
- **Archivos:** `app/workers/research_tasks.py`, `app/services/research_service.py`, `infra/docker/Dockerfile.research`

### 1.4 Dossier generation (2d)
- **Task `task_generate_dossier`:** Post-research, Qwen 9B genera business_description estructurado desde research data
- **Nuevo prompt:** `GENERATE_DOSSIER` en `app/llm/prompts.py`
- Input: research report + lead data + signals
- Output: JSON con business_description, key_findings, digital_maturity_assessment
- **Archivos:** `app/llm/prompts.py`, `app/llm/client.py`, `app/workers/tasks.py`

### 1.5 Export basico (1-2d)
- **Endpoints:**
  - `GET /leads/export?format=csv&status=qualified` -> CSV download
  - `GET /leads/export?format=json` -> JSON download
  - `GET /leads/{id}/export` -> ZIP con lead data + dossier + artifacts
- **Archivos:** `app/api/v1/leads.py`, `app/services/export_service.py`
- **Frontend:** Boton "Exportar" en leads page y lead detail

### 1.6 Dossier view en dashboard (2d)
- Agregar seccion "Dossier" en lead detail page (`dashboard/app/leads/[id]/page.tsx`)
- Mostrar: research status, confidence indicators, screenshots gallery, business description, detected signals con confidence
- Agregar API client functions: `getLeadResearch(leadId)`, `runResearch(leadId)`
- **Archivos:** `dashboard/app/leads/[id]/page.tsx`, `dashboard/lib/api/client.ts`, `dashboard/types/index.ts`

### 1.7 Pipeline integration (1d)
- Extender pipeline para HIGH leads: despues de `task_analyze_lead`, si `llm_quality == "high"`, encolar `task_research_lead` -> `task_generate_dossier`
- Agregar step tracking en `PipelineRun`
- **Archivo:** `app/workers/tasks.py`

---

## Phase 2 -- High Lead Commercial Brief

**Objetivo:** Generar evaluacion comercial interna para leads HIGH con dossier.
**Duracion estimada:** 2-3 semanas
**Criterio:** Lead HIGH con dossier tiene Commercial Brief completo. Brief visible en dashboard.

### 2.1 Commercial Brief model (1d)
- **Nuevo modelo `CommercialBrief`:**
  - lead_id (FK unique), research_report_id (FK nullable)
  - opportunity_score (Float 0-100)
  - budget_tier (enum: low/medium/high/premium)
  - estimated_budget_min (Float), estimated_budget_max (Float)
  - estimated_scope (enum: landing/institutional_web/catalog/ecommerce/redesign/automation/branding_web)
  - recommended_contact_method (enum: whatsapp/email/call/demo_first/manual_review)
  - should_call (enum: yes/no/maybe), call_reason (Text)
  - why_this_lead_matters (Text)
  - main_business_signals (JSON list)
  - main_digital_gaps (JSON list)
  - recommended_angle (Text)
  - demo_recommended (Bool)
  - contact_priority (enum: immediate/high/normal/low)
  - generator_model, reviewer_model (nullable), reviewed_at (nullable)
  - status (enum: pending/generated/reviewed/failed)
  - created_at, updated_at
- **Archivos:** `app/models/commercial_brief.py`, `app/models/__init__.py`, Alembic migration

### 2.2 Pricing matrix (1d)
- Agregar campo `pricing_matrix` (JSON) a `OperationalSettings`
- Default matrix:
  ```json
  {
    "landing": {"min": 300, "max": 600},
    "institutional_web": {"min": 500, "max": 1200},
    "catalog": {"min": 600, "max": 1500},
    "ecommerce": {"min": 1500, "max": 4000},
    "redesign": {"min": 400, "max": 1000},
    "automation": {"min": 800, "max": 3000},
    "branding_web": {"min": 1000, "max": 2500}
  }
  ```
- Configurable desde Settings UI
- **Archivos:** `app/models/settings.py`, `app/services/operational_settings_service.py`, migration

### 2.3 Brief generation (3-5d)
- **Task `task_generate_brief`:**
  1. Leer lead + research report + dossier
  2. LLM (EXECUTOR 9B) genera brief JSON desde prompt
  3. Lookup pricing matrix para budget estimation
  4. Guardar CommercialBrief
- **Nuevo prompt:** `GENERATE_COMMERCIAL_BRIEF` en `app/llm/prompts.py`
- Input: lead data + research report + dossier + pricing matrix
- Output: JSON con todos los campos del brief
- **Task `task_review_brief`:** REVIEWER 27B valida coherencia del brief
- **Archivos:** `app/llm/prompts.py`, `app/llm/client.py`, `app/services/brief_service.py`, `app/workers/tasks.py`

### 2.4 Opportunity score (2d)
- Combinar quality score (reglas, existente) con LLM-based opportunity assessment
- Factores LLM: negocio activo, presencia digital debil, potencial de mejora rapida, ticket estimado
- `opportunity_score` = weighted blend de rule score + LLM opportunity
- **Archivos:** `app/scoring/rules.py`, `app/services/brief_service.py`

### 2.5 Contact recommendation (1d)
- Logica basada en reglas + brief data:
  - No tiene web + Instagram activo + ticket alto -> WhatsApp + maybe call
  - Tiene web floja + email detectado -> Email
  - Ticket premium + negocio activo -> Call
  - Falta data suficiente -> manual_review
  - Opportunity score >80 + demo_recommended -> demo_first
- **Archivo:** `app/services/brief_service.py`

### 2.6 Brief view en dashboard (2d)
- Seccion "Commercial Brief" en lead detail page
- Mostrar: opportunity score gauge, budget tier badge, budget range, scope badge, contact recommendation, should_call indicator, call_reason, signals, gaps, angle
- API client: `getCommercialBrief(leadId)`, `generateBrief(leadId)`
- **Archivos:** `dashboard/app/leads/[id]/page.tsx`, `dashboard/lib/api/client.ts`, `dashboard/types/index.ts`

### 2.7 Enhanced draft generation (2d)
- Si lead tiene Commercial Brief, pasar brief context al prompt de draft generation
- Draft resultante menciona angulo recomendado, adapta tono segun contact recommendation
- **Archivos:** `app/outreach/generator.py`, `app/llm/prompts.py`

### 2.8 Pipeline integration (1d)
- Extender pipeline HIGH: `...dossier -> task_generate_brief -> task_review_brief -> task_generate_draft`
- **Archivo:** `app/workers/tasks.py`

---

## Phase 3 -- Outreach Intelligence

**Objetivo:** Drafts condicionados por brief. Runtime modes. Export avanzado.
**Duracion estimada:** 2 semanas
**Criterio:** Drafts HIGH son visiblemente mejores. Runtime controlable. Exports completos.

### 3.1 Runtime modes (2-3d)
- Agregar `runtime_mode` (enum: safe/assisted/auto) a `OperationalSettings`
- **Safe:** Todo requiere aprobacion manual. No auto-send. No auto-research.
- **Assisted:** Pipeline automatico. Drafts generados auto. Send requiere aprobacion.
- **Auto:** Pipeline + draft + send automatico para leads que cumplen criteria.
- Cada modo setea un conjunto de toggles atomicamente
- UI: Toggle prominente en ControlCenter
- **Archivos:** `app/models/settings.py`, `app/services/operational_settings_service.py`, `dashboard/components/dashboard/control-center.tsx`

### 3.2 Export avanzado (2d)
- Export XLSX con sheets: Leads, Dossiers, Briefs, Outreach
- Export ZIP para lead HIGH: lead.json + dossier.json + brief.json + drafts.json + screenshots/
- Endpoint: `POST /leads/export/batch` con filtros (status, quality, territory, date range)
- **Archivos:** `app/services/export_service.py`, `app/api/v1/leads.py`, `pyproject.toml` (agregar `openpyxl`)

### 3.3 Agent tools para nuevos features (1d)
- Agregar tools: `get_lead_dossier`, `get_commercial_brief`, `generate_research`, `generate_brief`, `export_lead`
- **Archivo:** `app/agent/tools/`

### 3.4 Notification enhancements (1d)
- Notificacion cuando dossier completo
- Notificacion cuando brief generado para lead HIGH
- Notificacion cuando brief tiene should_call=yes
- **Archivo:** `app/services/notification_emitter.py`

---

## Phase 4 -- Cockpit Dashboard

**Objetivo:** Evolucionar dashboard a AI operations cockpit.
**Duracion estimada:** 2-3 semanas
**Criterio:** Lead detail muestra dossier + brief + draft + timeline en un solo flow.

### 4.1 Lead detail redesign (3-5d)
- Layout 2-column: left = lead data + actions, right = contextual panel (dossier -> brief -> draft flow)
- Tabs en panel derecho: Dossier, Brief, Outreach, Timeline
- Score display con quality + opportunity dual gauge
- **Archivos:** `dashboard/app/leads/[id]/page.tsx`, nuevos componentes

### 4.2 Dossiers page (2d)
- Nueva pagina `/dossiers` con lista de research reports
- Filtros: status, confidence, territory
- **Archivos:** `dashboard/app/dossiers/page.tsx`

### 4.3 Briefs page (2d)
- Nueva pagina `/briefs` con lista de commercial briefs
- Filtros: budget_tier, contact_priority, should_call
- Sorteable por opportunity_score
- **Archivos:** `dashboard/app/briefs/page.tsx`

### 4.4 Runtime control panel (2d)
- Pagina `/runtime` o seccion prominente en `/panel`
- Modo global (Safe/Assisted/Auto) con indicador visual
- Toggle matrix por modulo: scraper, research, review, outreach, send
- Status de workers, queues, active tasks
- **Archivos:** `dashboard/app/panel/page.tsx` o `dashboard/app/runtime/page.tsx`

### 4.5 Sidebar update (1d)
- Agregar: Dossiers, Briefs a navegacion
- Agrupar logicamente: Discovery (Leads, Dossiers, Briefs), Outreach (Outreach, Respuestas), Ops (Panel, Rendimiento, Mapa, Activity)
- **Archivo:** `dashboard/components/layout/sidebar.tsx`

---

## Phase 5 -- Demo Infrastructure (dejar posterior)

**Objetivo:** Generar demos personalizadas para leads HIGH con brief favorable.
**Duracion estimada:** No estimar ahora. Requiere decisiones de arquitectura pendientes.
**Prerequisitos:** Phase 2 completa. Dominio `demo.scouter.ai` disponible. Claude Code integration path definido.

### 5.1 Scope tentativo
- Template system (landing pages base)
- Demo job worker (Claude Code SDK o API)
- Deploy pipeline (static hosting, preview URLs)
- Artifact linking (demo_url ligado a lead)
- Demo tracking (views, interactions)

### 5.2 Decisiones pendientes
- Claude Code SDK vs API vs subprocess
- Hosting: Vercel preview? Cloudflare Pages? Self-hosted?
- Template framework: plain HTML? Next.js static export?
- Cost model: solo para leads con opportunity_score >X y budget_tier >= high

### 5.3 Recomendacion
No invertir en esto hasta que Phase 2 este validada con datos reales. Si los Commercial Briefs no agregan valor medible, las demos tampoco lo haran.

---

## Commit Strategy

### Branching
- `main` para releases
- `feat/phase-0-stabilize` para Phase 0
- `feat/phase-1-dossier` para Phase 1
- `feat/phase-2-brief` para Phase 2
- Feature branches cortas (max 3 dias) mergeadas a la branch de fase

### Commits
Seguir convencion existente:
```
type: concise description

Types: feat, fix, chore, docs, refactor, security, build
```

---

## PR Breakdown

### Phase 0 PRs (5-6 PRs, 1 semana)
1. `security: fix WA/TG credential decrypt + update security audit doc`
2. `security: sanitize external data in LLM prompts + rate limit re-send`
3. `build: add .dockerignore, bind API port, add container health checks`
4. `feat: add Prometheus metrics endpoint`
5. `fix: add idempotency guards to pipeline tasks`
6. `test: add crypto, worker task, and idempotency tests`

### Phase 1 PRs (6-7 PRs, 2-3 semanas)
1. `feat: add LeadResearchReport and Artifact models + migration`
2. `feat: add confidence field to LeadSignal + migration`
3. `feat: add file storage service abstraction`
4. `feat: add Playwright research worker + Docker config`
5. `feat: add dossier generation task + LLM prompt`
6. `feat: add basic CSV/JSON export endpoints`
7. `feat: add dossier view to lead detail page`

### Phase 2 PRs (6-7 PRs, 2-3 semanas)
1. `feat: add CommercialBrief model + pricing matrix in settings`
2. `feat: add brief generation task + LLM prompt`
3. `feat: add opportunity score blending`
4. `feat: add contact recommendation engine`
5. `feat: add brief review task`
6. `feat: add brief view to dashboard + API client`
7. `feat: condition draft generation on commercial brief`

---

## Risks

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| Playwright worker consume demasiada RAM en Docker | Alta | Medio | Worker separado con memory limits, pool_size=1 |
| LLM briefs generan budget tiers inconsistentes | Media | Alto | Pricing matrix como constraint, REVIEWER valida, human approval |
| Research pipeline demasiado lento para batch | Media | Medio | Cola `research` separada, rate limit, skip si ya tiene research reciente |
| Screenshot storage crece rapido | Media | Bajo | Retention policy (30 dias), compresion, lazy loading |
| SQLite test divergence con nuevos modelos JSON | Alta | Medio | Evaluar Testcontainers con Postgres real |
| Playwright blocked por sites (captcha, WAF) | Media | Bajo | Graceful degradation: mark confidence=unknown, skip screenshot |
| Scope creep en Phase 2 (brief demasiado complejo) | Media | Alto | MVP brief con 5 campos core, iterar despues |

---

## Definition of Done by Phase

### Phase 0 -- Stabilize Reality
- [ ] `decrypt_safe()` en WA/TG service read paths, test manual exitoso
- [ ] Security audit findings PI-6/7/8, CC-7, CC-8 resueltos con tests
- [ ] `.dockerignore` existe, API port en 127.0.0.1, health checks en 3 containers
- [ ] `/metrics` endpoint activo, 3+ metricas custom registradas
- [ ] Idempotency guards en 4 tasks principales, con tests
- [ ] Tests para crypto round-trip
- [ ] Zero RED items en re-auditoria

### Phase 1 -- Lead Dossier Foundation
- [ ] Modelo `LeadResearchReport` con migration aplicada
- [ ] Modelo `Artifact` con migration aplicada
- [ ] `LeadSignal.confidence` field con migration
- [ ] Storage service funcional (local dev)
- [ ] Playwright research worker en Docker separado
- [ ] `task_research_lead` procesa un lead con website y genera report con screenshot
- [ ] `task_generate_dossier` genera business_description desde research data
- [ ] Pipeline HIGH encola research + dossier automaticamente
- [ ] Export CSV/JSON basico funciona desde API
- [ ] Dossier view visible en lead detail page del dashboard
- [ ] 5+ tests cubriendo research + dossier generation

### Phase 2 -- High Lead Commercial Brief
- [ ] Modelo `CommercialBrief` con migration aplicada
- [ ] Pricing matrix configurable en OperationalSettings
- [ ] `task_generate_brief` genera brief completo desde dossier + pricing
- [ ] `task_review_brief` REVIEWER valida brief
- [ ] Opportunity score calculado (blend rules + LLM)
- [ ] Contact recommendation funcional con logica de reglas
- [ ] Pipeline HIGH encola brief generation + review
- [ ] Draft generation condicionado por brief cuando existe
- [ ] Brief view visible en lead detail page
- [ ] Pricing matrix editable desde Settings UI
- [ ] 5+ tests cubriendo brief generation + review + recommendation

### Phase 3 -- Outreach Intelligence
- [ ] Runtime modes (safe/assisted/auto) funcionales
- [ ] Export XLSX + ZIP funcional
- [ ] Agent tools para dossier, brief, export
- [ ] Notifications para dossier/brief completados

### Phase 4 -- Cockpit Dashboard
- [ ] Lead detail rediseñado con panel contextual
- [ ] Paginas /dossiers y /briefs funcionales
- [ ] Runtime control visible en panel
- [ ] Sidebar reorganizado

### Phase 5 -- Demo Infrastructure
- [ ] Definicion de done se define cuando Phase 2 este validada
