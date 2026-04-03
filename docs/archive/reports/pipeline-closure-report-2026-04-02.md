# ClawScout — Pipeline Gap Closure Report

**Fecha:** 2026-04-02
**Branch:** `main`
**Commits:** `a9d4813`, `01136c6`, `37432ff`

---

## 1. Resumen Ejecutivo

Se cerraron los 6 gaps operativos identificados en la auditoria de pipeline runtime. El cambio mas critico fue la reestructuracion de `task_full_pipeline`: se reemplazo el `chain()` estatico de Celery por un dispatch secuencial donde cada task encadena al siguiente via `.delay()`. Esto integra la lane HIGH al pipeline real y elimina drafts duplicados.

**187 tests passing. TypeScript clean. Todo pusheado a main.**

---

## 2. Gaps Cerrados

### Gap 1: Pipeline chain — lane HIGH integrada (CRITICO)

**Problema:** `task_full_pipeline` usaba `chain(enrich, score, analyze, draft)` — el draft se generaba ANTES de que research/brief completaran para leads HIGH. Producía drafts duplicados y pobres.

**Solucion:**
- `task_full_pipeline` ahora es un simple dispatcher que solo llama `task_enrich_lead.delay()`
- Cada task encadena al siguiente cuando `pipeline_run_id` esta presente:
  - `task_enrich_lead` -> `task_score_lead`
  - `task_score_lead` -> `task_analyze_lead`
  - `task_analyze_lead` -> IF HIGH: `task_research_lead` ELSE: `task_generate_draft`
  - `task_research_lead` -> `task_generate_brief` (ya existia)
  - `task_generate_brief` -> `task_review_brief` (ya existia)
  - `task_review_brief` -> `task_generate_draft` (ya existia)
- Eliminado `task_generate_draft` del chain estatico
- Standalone task calls (sin pipeline_run_id) no encadenan — preserva compatibilidad

**Archivos:** `app/workers/tasks.py`

### Gap 2: Pipeline status tracking (CRITICO)

**Problema:** `task_review_brief` marcaba pipeline como "succeeded" ANTES de encadenar a draft. Pipeline status era mentiroso.

**Solucion:**
- Removido `pipeline_status="succeeded"` de `mark_task_succeeded` en `task_review_brief`
- Removido `update_pipeline_run(status="succeeded")` prematuro
- Solo `task_generate_draft` marca pipeline como finished/succeeded — es siempre el ultimo paso en ambos paths

**Archivos:** `app/workers/brief_tasks.py`

### Gap 3: Runtime mode con impacto real

**Problema:** `runtime_mode` era write-only. Ningun worker lo leia. No habia auto-send.

**Solucion:**
- En `task_generate_draft`, despues de generar draft exitosamente:
  - Si `require_approved_drafts == False` (modo auto): auto-approve draft
  - Si ademas `mail_enabled == True`: auto-send via SMTP
- Defaults seguros: solo activo en modo "auto" (require_approved_drafts=False)
- Frontend: control-center ahora lee `runtime_mode` del backend on load (era hardcoded "safe")

**Archivos:** `app/workers/tasks.py`, `dashboard/components/dashboard/control-center.tsx`

### Gap 4: Contact recommendation actionable

**Problema:** `should_call`, `recommended_contact_method`, `call_reason` eran decorativos.

**Solucion:**
- En `task_generate_draft`, antes de generar:
  - Si brief tiene `recommended_contact_method == "call"` o `"manual_review"`: skip auto-draft, marcar pipeline succeeded sin draft. Notificacion ya enviada por brief_service.
  - Si `recommended_contact_method == "whatsapp"` y lead tiene phone: generar WA draft como preferido
  - Si `recommended_contact_method == "email"`: comportamiento normal

**Archivos:** `app/workers/tasks.py`

### Gap 5: /dossiers page basada en datos reales

**Problema:** Mostraba leads HIGH como "candidatos" sin verificar si tenian dossier real.

**Solucion:**
- Reescrita la pagina completa
- Ahora fetchea `getLeadResearch(leadId)` para cada lead HIGH en paralelo
- Solo muestra leads con `research.status === "completed"`
- Muestra inline: website_confidence, cantidad de senales, duracion de research

**Archivos:** `dashboard/app/dossiers/page.tsx`

### Gap 6: Pricing matrix UI

**Problema:** Campo `pricing_matrix` existia en DB pero no tenia UI editable.

**Solucion:**
- Nuevo componente `PricingSection` con tabla editable (7 scopes x min/max USD)
- Botones Save/Reset con toast feedback via sileo
- Agregado como tab "Precios" en settings page
- Persiste como JSON string en `OperationalSettings.pricing_matrix`

**Archivos:** `dashboard/components/settings/pricing-section.tsx` (nuevo), `dashboard/components/settings/types.ts`, `dashboard/app/settings/page.tsx`

### Fix adicional: Runtime mode read-back

**Problema:** Control center hardcodeaba `useState("safe")` sin leer valor persistido.

**Solucion:** Agregado `setRuntimeModeState((data.runtime_mode as RuntimeMode) ?? "safe")` en `loadSettings()`.

**Archivos:** `dashboard/components/dashboard/control-center.tsx`, `dashboard/types/index.ts`

---

## 3. Pipeline Real Post-Fix

```
task_full_pipeline (dispatcher)
  |
  v
task_enrich_lead
  |
  v
task_score_lead
  |
  v
task_analyze_lead
  |
  +-- IF llm_quality == "high" -->  task_research_lead
  |                                   |
  |                                   v
  |                                 generate_dossier() inline
  |                                   |
  |                                   v
  |                                 task_generate_brief
  |                                   |
  |                                   v
  |                                 task_review_brief (REVIEWER 27B)
  |                                   |
  |                                   v
  +-- ELSE -----------------------> task_generate_draft
                                      |
                                      v
                                    IF auto mode: auto-approve + auto-send
                                      |
                                      v
                                    pipeline_run -> finished/succeeded
```

### Contact recommendation routing en draft
```
brief.recommended_contact_method == "call"           -> skip draft, pipeline done
brief.recommended_contact_method == "manual_review"  -> skip draft, pipeline done
brief.recommended_contact_method == "whatsapp"       -> prefer WA draft
brief.recommended_contact_method == "email"          -> normal email draft
brief == None                                        -> normal email draft
```

---

## 4. Archivos Tocados (9)

| Archivo | Tipo de cambio |
|---------|---------------|
| `app/workers/tasks.py` | Pipeline restructure, chain dispatch, contact routing, auto-approve |
| `app/workers/brief_tasks.py` | Remove premature pipeline finalization |
| `dashboard/app/dossiers/page.tsx` | Full rewrite — real research data |
| `dashboard/components/settings/pricing-section.tsx` | Nuevo — pricing matrix editor |
| `dashboard/components/settings/types.ts` | Add "pricing" tab |
| `dashboard/app/settings/page.tsx` | Add PricingSection render |
| `dashboard/components/dashboard/control-center.tsx` | Runtime mode read-back fix |
| `dashboard/types/index.ts` | Add runtime_mode, pricing_matrix to OperationalSettings |
| `alembic/versions/a0d285b111e7_merge_migration_heads.py` | Merge alembic heads |

---

## 5. Commits

| Commit | Descripcion | Archivos |
|--------|-------------|----------|
| `a9d4813` | fix: restructure pipeline chain — sequential dispatch, HIGH lane integrated | 2 |
| `01136c6` | feat: dossiers page real data + pricing matrix UI + runtime mode read-back | 6 |
| `37432ff` | fix: merge alembic migration heads | 1 |

---

## 6. Tests

- **187/187 passed** (0 failures, 1 deprecation warning)
- TypeScript: 0 errors (`npx tsc --noEmit` clean)
- No tests nuevos en esta corrida (los cambios son de wiring/orchestration, no de logica nueva)

---

## 7. Que Cambio vs Antes

| Aspecto | Antes | Despues |
|---------|-------|---------|
| Pipeline HIGH | Draft se generaba SIN esperar brief | Draft se genera DESPUES de brief/review |
| Draft duplicado | 2 drafts para leads HIGH | 1 solo draft (el correcto) |
| Pipeline status | Marcado succeeded prematuramente | Solo task_generate_draft marca finished |
| Runtime modes | Write-only, sin impacto | Auto-approve + auto-send en modo auto |
| Contact recommendation | Decorativo | Impacta canal de draft y skip |
| /dossiers | Candidatos HIGH sin verificar | Solo leads con dossier completado |
| Pricing matrix | Sin UI | Tabla editable en settings |
| Runtime mode UI | Hardcoded "safe" on load | Lee valor persistido |

---

## 8. Riesgos Remanentes

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| Batch pipeline sigue path separado | YELLOW | `task_batch_pipeline` usa loop inline, no el nuevo dispatch secuencial. HIGH leads en batch no pasan por research/brief |
| Playwright screenshots missing | LOW | Research es HTTP-only. Screenshots siempre null |
| Janitor no sweepea PipelineRun | YELLOW | PipelineRun stuck en "running" no se recupera automaticamente |
| correlation_id no propagado en brief chain | LOW | brief_tasks no acepta correlation_id |
| LLM fallback sin flag | LOW | Briefs con fallback data quedan como "generated" sin indicacion |

---

## 9. Que NO se toco

- Phase 5 / demos
- Playwright browser research
- Batch pipeline
- Refactors cosmeticos
- Rebranding adicional
- Tests de integracion con Postgres
