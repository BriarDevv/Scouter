# ClawScout — Code Restructuring Report

**Fecha:** 2026-04-03
**Branch:** `main`

---

## 1. Que Se Hizo

### Auditoria de estructura de codigo
Se auditaron los hotspots del repo contrastando contra `docs/architecture/audit.md`, `docs/architecture/target.md` y `docs/plans/refactor-roadmap.md`.

### PR 1: Split tasks.py god module
**Commit:** `60e372e`

El archivo `app/workers/tasks.py` (1,480 lineas, 14+ tasks) era el hotspot critico del repo. Se dividio en 5 archivos por dominio:

| Archivo nuevo | Tasks | Lineas |
|--------------|-------|--------|
| `pipeline_tasks.py` | task_full_pipeline, task_enrich_lead, task_score_lead, task_analyze_lead, task_generate_draft + helpers | ~700 |
| `review_tasks.py` | task_review_lead, task_review_draft, task_review_inbound_message, task_review_reply_assistant_draft | ~350 |
| `research_tasks.py` | task_research_lead | ~170 |
| `crawl_tasks.py` | task_crawl_territory | ~200 |
| `batch_tasks.py` | task_batch_pipeline, task_rescore_all | ~370 |

`tasks.py` quedo como re-export de 26 lineas para backward compatibility.

**Detalle tecnico:**
- Todos los tasks conservan `name="app.workers.tasks.task_xxx"` explicito para que el routing de Celery siga funcionando
- `celery_app.py` actualizado con imports de todos los nuevos modulos
- Tests actualizados con patch paths apuntando a los modulos reales
- `brief_tasks.py` (ya existente) no fue tocado

### PR 2: Split lead detail god page
**Commit:** `29d37c9`

El archivo `dashboard/app/leads/[id]/page.tsx` (1,263 lineas) era el hotspot frontend. Se dividio en 8 section components:

| Componente | Responsabilidad | Lineas |
|-----------|-----------------|--------|
| `lead-contact-card.tsx` | Info de contacto, score, signals | ~156 |
| `lead-analysis-section.tsx` | Summary LLM, quality, suggested angle | ~59 |
| `lead-dossier-section.tsx` | Research report, confidence, signals | ~159 |
| `lead-brief-section.tsx` | Commercial brief, budget, contact rec | ~165 |
| `lead-outreach-section.tsx` | Drafts, approve/reject | ~105 |
| `lead-pipeline-section.tsx` | Pipeline run history | ~62 |
| `lead-replies-section.tsx` | Inbound messages, reply drafts | ~150 |
| `lead-timeline-section.tsx` | Outreach logs, notes | ~60 |

`page.tsx` quedo como orquestador de ~543 lineas (state + data fetching + handlers + composition).

---

## 2. Resultados

| Metrica | Antes | Despues |
|---------|-------|---------|
| `app/workers/tasks.py` | 1,480 lineas | 26 lineas (re-exports) |
| `dashboard/app/leads/[id]/page.tsx` | 1,263 lineas | 543 lineas |
| Tests | 219 passing | 219 passing |
| TypeScript | Clean | Clean |
| Archivos nuevos backend | 0 | 5 task files |
| Archivos nuevos frontend | 0 | 8 section components |

---

## 3. Que Queda Por Hacer (Plan Aprobado)

### PR 3: Agrupar services/ por dominio (PENDIENTE)
Mover los 38 archivos planos de `app/services/` a subdirectorios por dominio:
- `services/leads/`, `services/outreach/`, `services/inbox/`, `services/pipeline/`, `services/research/`, `services/notifications/`, `services/settings/`, `services/comms/`
- Re-exports en `__init__.py` para backward compat

### PR 4: Split control-center.tsx (PENDIENTE)
Dividir el componente de 684 lineas en:
- `pipeline-controls.tsx`, `crawl-controls.tsx`, `runtime-mode-panel.tsx`, `feature-toggles.tsx`, `health-dots.tsx`

### PR 5: Unificar batch pipeline (OPCIONAL)
Hacer que batch_pipeline use el mismo dispatch secuencial que single-lead.

### Ideas adicionales del Plan agent (para futuro)
- **Task harness**: Extraer la ceremonia de tracking (87 calls repetitivas) en un context manager reutilizable — cada task pasaria de ~100 lineas a ~15-20
- **LLM client migration**: Migrar 15 funciones legacy a `invoke_structured`/`invoke_text` (solo 3 de 18 ya usan la API nueva)
- **Guardrail tests**: Agregar tests arquitecturales que prevengan regresion (no imports privados de LLM, no Redis directo en API, etc.)
- **Pipeline step registry**: Centralizar la logica de chaining (`.delay()`) en un solo lugar legible

---

## 4. Que Ya Esta Bien y NO Conviene Tocar

| Area | Por que dejarlo |
|------|-----------------|
| `app/models/` | Bien estructurado, UUID PKs, relaciones limpias |
| `app/llm/` | Foundation solida: contracts, invocation_metadata, prompt_registry, sanitizer |
| `app/crawlers/` | Simple, funciona |
| `app/scoring/` | Pequeno, single-purpose |
| `app/mail/` | Provider abstraction limpia |
| `app/db/` | Standard, correcto |
| `app/core/` | Config, crypto, logging — estable |
| `docs/` | Jerarquia ya curada |
| Full `app/modules/` migration | Prematuro — necesita boundaries primero |
| Frontend server components | Cambio grande, producto todavia evolucionando |
| Generated API client/types | Requiere tooling OpenAPI, no urgente |
| `OperationalSettings` split | Funciona como singleton por ahora |

---

## 5. Deuda Estructural Restante (Priorizada)

### Critica
- ~~`app/workers/tasks.py` (1,480L god module)~~ **RESUELTO**

### Alta
- ~~`dashboard/app/leads/[id]/page.tsx` (1,263L god page)~~ **RESUELTO**
- `app/services/` como capa plana (38 archivos sin agrupacion) — PR 3 pendiente
- `app/workflows/batch_pipeline.py` mezcla orchestration con execution — PR 5 pendiente

### Media
- `dashboard/components/dashboard/control-center.tsx` (684L) — PR 4 pendiente
- `dashboard/lib/api/client.ts` (699L) manual, drift risk
- `dashboard/types/index.ts` (855L) manual, drift risk
- `app/llm/client.py` (1,529L) — 15 funciones legacy sin structured outputs

### Baja
- `app/schemas/` reorganizacion — thin DTOs, bajo impacto
- Transaction boundary refactoring — invasivo, necesita su propio esfuerzo
- OpenTelemetry — Prometheus auto-instrumentation cubre lo basico

---

## 6. Commits

| Commit | Descripcion | Archivos |
|--------|-------------|----------|
| `60e372e` | refactor: split tasks.py god module into domain task files | 8 |
| `29d37c9` | refactor: split lead detail god page into section components | 9 |

---

## 7. Verificacion

- **Tests:** 219/219 passed
- **TypeScript:** 0 errors
- **Ruff:** 0 nuevas violaciones (12 pre-existentes)
- **Backward compat:** tasks.py re-exports, Celery task names preservados con `name=` explicito
