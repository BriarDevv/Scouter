# Scouter Pipeline Runtime Audit

**Fecha:** 2026-04-02
**Branch:** `main`
**Metodologia:** Inspeccion de codigo real — task chains, service calls, data contracts, DB constraints.

---

## 1. Executive Summary

El pipeline de Scouter tiene todas las piezas implementadas, pero **la cadena principal (`task_full_pipeline`) no integra la lane HIGH**. El flujo de Celery `chain()` salta de `analyze` a `draft`, corriendo la generacion de draft EN PARALELO con research/brief en vez de DESPUES. Esto significa que los drafts de leads HIGH se generan sin considerar el dossier ni el brief comercial.

Las piezas individuales (research, dossier LLM, brief generation, brief review) estan wired correctamente entre si via `.delay()` chains. El problema es que `task_full_pipeline` no las incluye en su cadena Celery, y `task_generate_draft` corre sin esperar a que el flujo HIGH complete.

**Runtime modes** existen en la DB y UI pero no impactan el comportamiento del pipeline (write-only). Las **notifications** estan correctamente wired. Los **exports** funcionan. El **dashboard** muestra datos reales pero las paginas `/dossiers` y `/briefs` dependen de data que solo se genera si el pipeline HIGH completa.

**Estado general: PARTIAL — piezas existen, cadena principal rota.**

---

## 2. Expected Pipeline vs Real Pipeline

### Esperado (propuesta)
```
lead -> enrich -> score -> analyze
  -> IF HIGH: research -> dossier -> brief -> review_brief -> draft (condicionado)
  -> IF NOT HIGH: draft directo
-> approval -> send -> inbound/reply loop
```

### Real (codigo)
```
task_full_pipeline dispatches Celery chain():
  enrich -> score -> analyze -> draft   (SIEMPRE, sin condicion)

SIDE EFFECT from task_analyze_lead:
  IF llm_quality == "high":
    task_research_lead.delay()           (fire-and-forget, NO espera)
      -> generate_dossier() inline
      -> on_research_completed notification
      -> task_generate_brief.delay()
        -> on_brief_generated notification
        -> task_review_brief.delay()
          -> task_generate_draft.delay() (SEGUNDO draft, duplicado)
```

### Resultado real
Para un lead HIGH, se generan **DOS drafts**:
1. Uno desde la cadena principal (sin brief context)
2. Otro desde `task_review_brief` (con brief context, si la cadena lateral completa)

Para un lead NO-HIGH, funciona correctamente (solo la cadena principal).

---

## 3. Stage-by-Stage Runtime Map

| Etapa | Task | Trigger | Automatico? | Solo HIGH? | Output |
|-------|------|---------|-------------|------------|--------|
| Ingestion | Google Maps crawler | Manual via UI/API | No | No | Lead row in DB |
| Enrichment | `task_enrich_lead` | Pipeline chain | Si | No | Signals, email, website analysis |
| Scoring | `task_score_lead` | Pipeline chain | Si | No | score (0-100), scored_at |
| LLM Analysis | `task_analyze_lead` | Pipeline chain | Si | No | llm_summary, llm_quality, llm_suggested_angle |
| Research | `task_research_lead` | Side-effect .delay() from analyze | Si (si HIGH) | Si | LeadResearchReport row |
| Dossier | `generate_dossier()` inline | Called inside task_research_lead | Si (si research ok) | Si | business_description on report |
| Brief | `task_generate_brief` | Chained from research | Si (si pipeline) | Si | CommercialBrief row |
| Brief Review | `task_review_brief` | Chained from brief | Si | Si | reviewer_model, reviewed_at, status |
| Draft Generation | `task_generate_draft` | Pipeline chain (principal) + chain from review_brief (lateral) | Si | No | OutreachDraft row |
| Approval | Manual via UI/API | No | Manual | No | draft.status -> approved |
| Send | Manual via UI/API | No | Manual | No | OutreachDelivery row |
| Inbound | IMAP sync | Manual trigger or periodic | Semi-auto | No | InboundMessage, EmailThread |
| Classification | LLM classify | Auto if auto_classify enabled | Configurable | No | classification_label, summary |
| Reply Draft | LLM generate | Manual trigger | No | No | ReplyAssistantDraft |
| Reply Review | LLM review | Manual trigger | No | No | ReplyAssistantReview |
| Reply Send | SMTP | Manual trigger | No | No | ReplyAssistantSend |

---

## 4. Current State by Stage

| Etapa | Estado | Justificacion |
|-------|--------|---------------|
| Lead Ingestion | DONE | Google Maps crawler funciona, dedup via SHA-256 |
| Enrichment | DONE | httpx website analysis, signal detection, email extraction |
| Scoring | DONE | Rules-based, 4 dimensiones, capped 0-100 |
| LLM Analysis | DONE | Summary + quality evaluation via Qwen 9B |
| Research | PARTIAL | Funciona pero es fire-and-forget desde analyze, no bloqueante |
| Dossier | PARTIAL | `generate_dossier()` se llama inline en research task, pero el resultado solo se guarda en `business_description` del report — no genera un artifact separado |
| Brief Generation | PARTIAL | Se genera si research completa y esta en pipeline, pero el brief no llega antes del draft principal |
| Brief Review | PARTIAL | Task existe, se encadena desde brief, pero el review no impacta el draft ya generado por la cadena principal |
| Draft (condicionado) | BROKEN | El draft de la cadena principal se genera SIN esperar brief. El segundo draft (desde review_brief) duplica |
| Approval | DONE | Manual via UI, status change persisted |
| Send (Email) | DONE | SMTP con delivery tracking, rate limit (CC-7) |
| Send (WhatsApp) | DONE | Kapso API, dry_run flag |
| Inbound Sync | DONE | IMAP fetch, dedup, thread matching mejorado (CC-8) |
| Classification | DONE | LLM classify con optimistic lock |
| Reply Assistant | DONE | Generate + review + send con thread headers |
| Runtime Modes | NOT_INTEGRATED | DB field existe, UI funciona, pero NINGUN worker/service lee runtime_mode |
| Exports | DONE | CSV/JSON/XLSX funcionan via `/leads/export` |
| Notifications (dossier/brief) | DONE | Wired en task_research_lead y brief_service |

---

## 5. Data Contracts Between Stages

### enrich -> score
- **Produce:** `Lead.enriched_at`, `Lead.signals[]`, `Lead.email`, `Lead.website_url`
- **Consume:** `scoring/rules.py` lee signals, industry, completeness, Google Maps data
- **Estado:** OK — contrato solido

### score -> analyze
- **Produce:** `Lead.score`, `Lead.scored_at`
- **Consume:** `evaluate_lead_quality` recibe score como parametro
- **Estado:** OK

### analyze -> research (HIGH)
- **Produce:** `Lead.llm_quality`, `Lead.llm_summary`, `Lead.llm_suggested_angle`
- **Consume:** `task_research_lead` no consume estos campos directamente — solo verifica existencia de lead
- **Estado:** PARTIAL — research podria usar llm_summary como context pero no lo hace

### research -> dossier
- **Produce:** `LeadResearchReport` con signals_json, html_metadata, website/instagram/whatsapp confidence
- **Consume:** `generate_dossier()` recibe estos campos como parametros
- **Estado:** OK — wired inline en task_research_lead

### research -> brief
- **Produce:** Same LeadResearchReport
- **Consume:** `brief_service.generate_brief()` lee report via DB query
- **Estado:** OK — lee report correctamente

### brief -> draft (ROTO)
- **Produce:** `CommercialBrief` con recommended_angle, budget, contact recommendation
- **Consume:** `generator.py` hace query `CommercialBrief.filter_by(lead_id=lead.id)` y usa `recommended_angle`
- **Estado:** BROKEN — el draft de la cadena principal se genera ANTES de que el brief exista

### Outputs que nadie consume
- `CommercialBrief.should_call` — no impacta ningun flujo automatico
- `CommercialBrief.recommended_contact_method` — no redirige a canal WA vs email
- `CommercialBrief.contact_priority` — no ordena ningun queue
- `CommercialBrief.demo_recommended` — no dispara nada (Phase 5 postergada)
- `LeadResearchReport.screenshots_json` — siempre null (no hay Playwright)

---

## 6. High Lead Lane Audit

### Lo que deberia pasar
1. Lead scored como HIGH
2. Research ejecuta investigacion web
3. Dossier generado desde research data
4. Brief comercial con budget/opportunity/contact
5. Reviewer valida brief
6. Draft generado CON context del brief
7. Approval manual

### Lo que realmente pasa
1. Lead scored como HIGH — OK
2. `task_analyze_lead` detecta HIGH y dispara `task_research_lead.delay()` — OK pero fire-and-forget
3. **AL MISMO TIEMPO**, la cadena Celery principal avanza a `task_generate_draft` — PROBLEMA
4. Research completa, genera dossier — OK
5. Research encadena a `task_generate_brief` — OK
6. Brief encadena a `task_review_brief` — OK
7. Review brief encadena a `task_generate_draft.delay()` — DUPLICADO
8. Ahora hay 2 drafts: uno pobre (sin brief) y uno rico (con brief)

### Severidad: RED
El flujo HIGH no funciona como se espera. El draft "rico" existe pero es un duplicado innecesario.

---

## 7. Dossier Integration Audit

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Modelo `LeadResearchReport` | DONE | Con confidence levels, signals, metadata |
| `run_research()` service | DONE | httpx website analysis, signal detection |
| `generate_dossier()` LLM | DONE | Se llama desde task_research_lead |
| Resultado almacenado | PARTIAL | Solo `business_description` en report, no artifact separado |
| Dashboard dossier section | DONE | Lead detail muestra research data |
| `/dossiers` page | PARTIAL | Muestra leads HIGH como "candidatos", no filtra por research existente |
| Playwright screenshots | MISSING | `screenshots_json` siempre null |
| Dossier como artifact descargable | MISSING | No hay PDF/export del dossier individual |

---

## 8. Commercial Brief Integration Audit

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| Modelo `CommercialBrief` | DONE | Todos los campos de la propuesta |
| `generate_brief()` service | DONE | LLM + pricing matrix + inference helpers |
| Pricing matrix configurable | PARTIAL | Campo en DB, default en servicio, sin UI para editar |
| `should_call` / `call_reason` | DONE (estructura) | Campos se llenan via LLM, pero no impactan flujo |
| `recommended_contact_method` | DONE (estructura) | No redirige draft a WA vs email automaticamente |
| `opportunity_score` | DONE | Blend de LLM-based assessment |
| `budget_tier` / budget range | DONE | Inferido desde pricing matrix + estimated_scope |
| Brief review (REVIEWER) | DONE | Task encadenada, marca reviewed_at |
| Dashboard brief section | DONE | Lead detail muestra todos los campos |
| `/briefs` page | DONE | Lista briefs reales via API |
| Brief condiciona draft | PARTIAL | `generator.py` busca brief y usa `recommended_angle`, pero solo funciona si brief existe ANTES del draft |

---

## 9. Draft / Review / Send Flow Audit

| Aspecto | Estado |
|---------|--------|
| Draft generation (email) | DONE |
| Draft generation (WhatsApp) | DONE (si WA outreach enabled y lead tiene phone) |
| Draft condicionado por brief | BROKEN (timing issue — draft antes que brief) |
| Quality gate (solo HIGH con email) | DONE |
| Approval workflow | DONE |
| Send via SMTP | DONE con delivery tracking |
| Send rate limit (CC-7) | DONE — max 3, 5min cooldown |
| Send via Kapso (WA) | DONE |

---

## 10. Inbound / Reply Loop Audit

| Aspecto | Estado |
|---------|--------|
| IMAP sync | DONE |
| Thread matching (Message-ID first) | DONE (CC-8) |
| Subject fallback (confidence 0.3) | DONE |
| Reply classification (LLM) | DONE |
| Auto-classify toggle | DONE |
| Reply assistant generation | DONE |
| Reply review (REVIEWER) | DONE |
| Reply send with thread headers | DONE |
| Notification on classified reply | DONE |

---

## 11. Runtime Modes / Toggles Audit

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| `runtime_mode` field en DB | DONE | "safe" / "assisted" / "auto" |
| `apply_runtime_mode()` API | DONE | Sets toggles atomically |
| UI selector en ControlCenter | DONE | 3 botones con color indicator |
| **runtime_mode leido por workers** | **NOT_INTEGRATED** | **Ningun task/service lee runtime_mode** |
| Individual toggles (mail, WA, reviewer, etc.) | DONE | Estos SI se leen y respetan |
| `require_approved_drafts` | DONE | Setteado por runtime_mode presets |
| Auto-send en modo "auto" | MISSING | No hay logica de auto-send post-draft |

### Conclusion
Runtime modes funcionan como atajo para setear toggles individuales. Eso es util. Pero no hay logica que diga "si estamos en modo auto, enviar draft automaticamente". El modo solo cambia checkboxes.

---

## 12. Dashboard Reality Check

| Pagina | Muestra datos reales? | Depende del pipeline? | Estado |
|--------|-----------------------|----------------------|--------|
| `/panel` | Si — stats, pipeline, activity | Si | DONE |
| `/leads` | Si — leads reales | Si | DONE |
| `/leads/[id]` dossier section | Si — research report real | Solo si pipeline HIGH completa | PARTIAL |
| `/leads/[id]` brief section | Si — brief real | Solo si pipeline HIGH completa | PARTIAL |
| `/dossiers` | NO — muestra leads HIGH como candidatos | No filtra por research existente | PARTIAL |
| `/briefs` | Si — llama `listBriefs()` | Depende de briefs generados | DONE (pero puede estar vacio) |
| `/outreach` | Si — drafts reales | Si | DONE |
| `/responses` | Si — inbound real | Si | DONE |
| `/performance` | Si — analytics reales | Si | DONE |
| `/map` | Si — leads con coords | Si | DONE |
| `/activity` | Si — tasks reales | Si | DONE |
| `/settings` runtime mode | Si — toggles reales | Parcial (modes no impactan pipeline) | PARTIAL |
| Export | Si — funcional | Independiente | DONE |

---

## 13. Reliability / Failure Modes

### Que pasa si research falla
- `task_research_lead` marca report como FAILED
- La cadena lateral (brief, review, draft-from-review) NO se dispara
- La cadena principal (draft SIN brief) SI sigue corriendo
- **Resultado:** lead HIGH recibe draft sin investigacion. Acceptable degradation.

### Que pasa si brief falla
- `task_generate_brief` marca brief como FAILED
- `task_review_brief` no se encadena
- La cadena principal ya genero el draft
- **Resultado:** draft sin contexto de brief. Acceptable degradation.

### Que pasa si Ollama falla
- `_call_ollama_chat` retries 3 veces con backoff exponencial
- Si falla despues de retries: funciones retornan fallback values
- `generate_dossier()` retorna dict con defaults
- `generate_commercial_brief()` retorna dict con manual_review recommendation
- **Resultado:** datos parciales pero no crash. OK.

### Que pasa si review_brief falla
- Brief queda en estado GENERATED (no REVIEWED)
- `task_generate_draft.delay()` desde review_brief no se ejecuta
- La cadena principal ya genero un draft
- **Resultado:** brief sin review, pero draft existe. OK.

### Race condition: draft duplicado
- La cadena principal genera draft sin brief
- `task_review_brief` genera segundo draft con brief
- Ambos quedan como `pending_review`
- **Resultado:** usuario ve 2 drafts para el mismo lead. CONFUSO pero no destructivo.

### Pipeline tracking gaps
- `task_full_pipeline` marca pipeline como "running" al despachar la chain
- Cada task individual actualiza step y status
- `task_generate_draft` marca pipeline como "succeeded" al final
- PERO: la cadena lateral (research -> brief -> review -> draft) NO actualiza el pipeline_run status. El pipeline se marca "succeeded" cuando el primer draft termina, no cuando toda la cadena HIGH termina.

---

## 14. Observability / Metrics / Logging

| Aspecto | Estado |
|---------|--------|
| structlog con lead_id binding | DONE |
| pipeline_run_id propagation | DONE (en cadena principal), PARTIAL (en cadena lateral) |
| task_id tracking | DONE |
| Prometheus HTTP metrics | DONE (auto-instrumented) |
| Custom Prometheus counters | MISSING |
| LLM call duration tracking | MISSING |
| LLM token cost tracking | MISSING |
| End-to-end lead journey trace | PARTIAL — seguible via logs pero no hay dashboard de tracing |

### Podemos debuggear un HIGH lead?
Si, pero con esfuerzo:
1. `lead_id` esta en todos los logs de tasks
2. `pipeline_run_id` esta en la cadena principal
3. La cadena lateral (research -> brief) tiene `lead_id` pero `pipeline_run_id` solo si viene del pipeline
4. No hay vista consolidada "todo lo que paso con este lead"

---

## 15. Security / Risk Notes

| Item | Estado |
|------|--------|
| LLM input sanitization (PI-6/7/8) | DONE — sanitizer.py |
| Draft re-send rate limit (CC-7) | DONE — max 3, 5min cooldown |
| Thread matching tightened (CC-8) | DONE — confidence 0.3, email check |
| Credentials encrypted at rest | DONE — Fernet |
| Decrypt on read (WA/TG) | DONE — fixed |
| API key auth | DONE |
| CORS restricted | DONE |

---

## 16. Proposal-to-Runtime Gap List

| # | Propuesta | Estado Real | Gap |
|---|-----------|-------------|-----|
| 1 | Research con Playwright (screenshots, DOM) | httpx-only, sin screenshots | Screenshots missing, Playwright no integrado |
| 2 | Dossier como artifact descargable | Solo campo business_description en report | No hay PDF/export individual |
| 3 | Brief condiciona draft | Draft se genera ANTES del brief | Timing roto en cadena principal |
| 4 | should_call redirige a canal | Campo existe pero no impacta flujo | No hay routing automatico |
| 5 | recommended_contact_method elige canal | Campo existe pero no impacta | Draft siempre es email + WA opcional |
| 6 | Runtime modes impactan operacion | Solo setean toggles, no hay auto-send | No hay logica "modo auto" real |
| 7 | Pricing matrix editable desde UI | Campo en DB, sin UI | No hay settings section |
| 8 | Cockpit dashboard (panel derecho contextual) | Dashboard con secciones colapsables | No hay panel derecho persistente |
| 9 | Demo generation | No implementado (Phase 5) | Postergado correctamente |
| 10 | Confidence signals con niveles | Modelo tiene confidence, research los genera | Enrichment original no genera confidence |

---

## 17. Top Missing Links

1. **Pipeline chain no incluye lane HIGH** — `task_full_pipeline` va directo de analyze a draft
2. **Draft generado sin esperar brief** — timing issue en Celery chain
3. **runtime_mode no leido por ningun worker** — write-only
4. **should_call/contact_method no impactan flujo** — datos decorativos
5. **No hay auto-send en modo "auto"** — require_approved_drafts cambia pero no hay send automatico
6. **Screenshots missing** — research es HTTP-only, no browser
7. **Pricing matrix sin UI** — no editable desde dashboard
8. **Pipeline status no refleja cadena lateral** — se marca "succeeded" antes de que HIGH complete
9. **/dossiers page no filtra por research existente** — muestra candidatos, no resultados
10. **Enrichment original no genera confidence levels** — solo research los genera

---

## 18. Recommended Immediate Fixes

### Fix 1: Reestructurar `task_full_pipeline` (CRITICO)
La cadena Celery debe bifurcarse:
- Para leads NO-HIGH: `enrich -> score -> analyze -> draft`
- Para leads HIGH: `enrich -> score -> analyze -> research -> brief -> review_brief -> draft`

Esto requiere que `task_full_pipeline` sea una tarea de orquestacion (no un simple `chain()`) que decida el path despues de analyze.

### Fix 2: Eliminar draft duplicado desde review_brief
`task_review_brief` no deberia encadenar `task_generate_draft` si el pipeline principal ya lo hizo. O mejor: el pipeline principal NO deberia generar draft para HIGH leads.

### Fix 3: Pipeline status debe reflejar cadena completa
`pipeline_run` debe mantenerse "running" hasta que la ultima etapa (draft) complete, incluyendo la cadena lateral.

### Fix 4: Agregar auto-send en modo "auto"
Despues de generar draft, si `runtime_mode == "auto"` y `require_approved_drafts == False`, auto-aprobar y enviar.

### Fix 5: Pricing matrix UI
Agregar seccion en settings para editar `pricing_matrix` como JSON editable.

---

## 19. Open Questions / Hypotheses to Validate

1. **H1:** La idempotency guard en `task_generate_draft` (skip si draft existente pending/approved) podria prevenir el draft duplicado parcialmente — pero depende de timing de la race condition.
2. **H2:** El enrichment podria generar confidence levels sin necesidad de research separado — seria suficiente?
3. **H3:** Separar `task_full_pipeline` en orquestador seria mejor que tener dos chains paralelas.
4. **H4:** Conviene que `should_call` y `contact_method` impacten el canal de draft automaticamente, o es mejor dejarlo como dato advisory?
5. **H5:** Los leads procesados hasta ahora por batch pipeline — tienen dossiers/briefs o solo pasaron por la cadena original?
