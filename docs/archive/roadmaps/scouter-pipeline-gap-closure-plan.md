# Scouter Pipeline Gap Closure Plan

**Fecha:** 2026-04-02
**Basado en:** `docs/archive/audits/scouter-pipeline-runtime-audit.md`

---

## 1. What Must Be Fixed First

### 1.1 Reestructurar `task_full_pipeline` (CRITICO)

**Problema:** La cadena Celery `chain(enrich, score, analyze, draft)` no incluye la lane HIGH. Research/brief/review corren como side-effect paralelo, y el draft se genera SIN esperar el brief.

**Solucion:** Convertir `task_full_pipeline` en un orquestador que bifurca:

```python
# Pseudocodigo
enrich(lead) -> score(lead) -> analyze(lead)
if llm_quality == "high":
    research(lead) -> brief(lead) -> review_brief(lead) -> draft(lead)
else:
    draft(lead)
```

**Implementacion concreta:**
- Eliminar el `chain()` de 4 pasos
- Cada task chaina al siguiente via `.delay()` al final de su ejecucion (pattern que ya existe en analyze -> research)
- `task_enrich_lead` -> chain `task_score_lead.delay()`
- `task_score_lead` -> chain `task_analyze_lead.delay()`
- `task_analyze_lead` -> IF HIGH: chain `task_research_lead.delay()` (ya existe), ELSE: chain `task_generate_draft.delay()`
- `task_research_lead` -> chain `task_generate_brief.delay()` (ya existe)
- `task_generate_brief` -> chain `task_review_brief.delay()` (ya existe)
- `task_review_brief` -> chain `task_generate_draft.delay()` (ya existe)
- Remover `task_generate_draft` del `chain()` original

**Archivos:** `app/workers/tasks.py` (task_full_pipeline, task_enrich_lead, task_score_lead)

### 1.2 Eliminar draft duplicado

**Problema:** Si la lane HIGH funciona, `task_review_brief` encadena `task_generate_draft` que es el mismo que la cadena principal ya disparo.

**Solucion:** Con Fix 1.1, el draft SOLO se genera al final del path correspondiente. La idempotency guard existente (`skip si draft pending/approved existe`) actua como safety net.

**Archivos:** Ninguno extra si Fix 1.1 se implementa correctamente.

### 1.3 Pipeline status debe cubrir cadena completa

**Problema:** `pipeline_run` se marca "succeeded" cuando el primer `task_generate_draft` termina, no cuando la cadena HIGH completa.

**Solucion:** Solo marcar `pipeline_run` como "succeeded" + "finished" en `task_generate_draft` (que siempre es el ultimo paso en ambos paths). Eliminar el `update_pipeline_run(finished=True)` de steps intermedios.

**Archivos:** `app/workers/tasks.py` (task_analyze_lead — no marcar finished), `app/workers/brief_tasks.py` (task_review_brief — no marcar finished, solo update step)

---

## 2. What Must Be Wired Next

### 2.1 Runtime mode impacta operacion real

**Problema:** `runtime_mode` es write-only. Ningun worker lo lee.

**Solucion:** No cambiar workers — el pattern actual (runtime_mode setea toggles individuales) ya es correcto. Lo que falta:
- En modo "auto": agregar logica post-draft que auto-aprueba y auto-envia si `require_approved_drafts == False`
- En `task_generate_draft`, despues de crear el draft: check settings, si `require_approved_drafts == False`, auto-aprobar y encolar send

**Archivos:** `app/workers/tasks.py` (task_generate_draft)

### 2.2 should_call / contact_method impactan draft

**Problema:** Datos decorativos — no impactan que tipo de draft se genera.

**Solucion:** En `task_generate_draft`:
- Si `recommended_contact_method == "whatsapp"` y lead tiene phone: generar WA draft como draft principal (no solo como secondary)
- Si `recommended_contact_method == "call"`: no generar draft automatico, solo notificacion de "llamar"
- Si `recommended_contact_method == "manual_review"`: no generar draft, solo notificacion

**Archivos:** `app/workers/tasks.py` (task_generate_draft), `app/services/notification_emitter.py` (agregar `on_call_recommended`)

### 2.3 Pricing matrix UI en settings

**Problema:** Campo en DB pero sin UI.

**Solucion:** Agregar seccion en settings page con JSON editor o form de rangos por scope.

**Archivos:** `dashboard/components/settings/` (nueva seccion), `dashboard/app/settings/page.tsx`

### 2.4 /dossiers page filtra por research existente

**Problema:** Muestra leads HIGH como candidatos, no como leads con dossier real.

**Solucion:** Agregar endpoint `/leads?has_research=true` o usar el existente `/leads` con filtro, y en frontend filtrar los que tienen research report.

**Archivos:** `dashboard/app/dossiers/page.tsx`, opcionalmente `app/api/v1/leads.py`

---

## 3. What Can Wait

| Item | Razon para postergar |
|------|---------------------|
| Playwright browser research | Research httpx funciona para MVP. Playwright requiere worker Docker separado con Chromium |
| Dossier como PDF artifact | El business_description en report es suficiente por ahora |
| Observability dashboard (traces) | Logs con structlog son suficientes para debugging manual |
| Custom Prometheus counters | Auto-instrumented metrics cubren lo basico |
| End-to-end lead journey view | Se puede reconstruir via logs por lead_id |
| Contact priority queue ordering | Dato util pero no bloquea operacion |
| Demo infrastructure (Phase 5) | Postergado por decision explicita |

---

## 4. Minimal Changes to Make the Proposal Operational

### Cambio 1: Pipeline orquestador (no chain estatico)
```
task_full_pipeline -> despacha enrich
enrich.on_success -> despacha score
score.on_success -> despacha analyze
analyze.on_success -> IF HIGH: despacha research ELSE: despacha draft
research.on_success -> despacha brief
brief.on_success -> despacha review_brief
review_brief.on_success -> despacha draft
draft.on_success -> IF auto mode: auto-approve + send
```

### Cambio 2: Auto-send en modo auto
En `task_generate_draft`, despues de generar draft exitosamente:
```python
ops = get_cached_settings(db)
if not ops.require_approved_drafts:
    # Auto-approve
    draft.status = DraftStatus.APPROVED
    draft.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    # Auto-send
    from app.services.mail_service import send_draft
    try:
        send_draft(db, draft.id)
    except Exception:
        pass  # Draft queda approved, send se puede reintentar
```

### Cambio 3: Draft routing por contact_method
En `task_generate_draft`, si hay brief con `recommended_contact_method`:
- `whatsapp`: generar WA draft como primary
- `email`: generar email draft (actual behavior)
- `call` / `manual_review`: skip draft, emitir notificacion

### Cambio 4: Pipeline status tracking correcto
Solo `task_generate_draft` marca `pipeline_run` como finished.

---

## 5. Recommended Execution Order

| Orden | Cambio | Esfuerzo | Impacto |
|-------|--------|----------|---------|
| 1 | Reestructurar pipeline chain | 4h | CRITICO — arregla la lane HIGH |
| 2 | Pipeline status tracking | 1h | Necesario para observabilidad |
| 3 | Auto-send en modo auto | 2h | Completa runtime modes |
| 4 | Draft routing por contact_method | 2h | Hace brief actionable |
| 5 | /dossiers page con filtro real | 1h | UX fix |
| 6 | Pricing matrix UI | 3h | Completa settings |

---

## 6. Commit / PR Strategy

```
1. fix: restructure pipeline to sequential dispatch (remove static chain)
   - task_full_pipeline como orquestador
   - cada task chaina al siguiente
   - lane HIGH integrada

2. fix: pipeline status tracks full chain including HIGH lane
   - solo task_generate_draft marca finished
   - steps intermedios actualizan step sin finished

3. feat: auto-approve and auto-send in auto runtime mode
   - task_generate_draft auto-approves si require_approved_drafts=false
   - auto-send via mail_service

4. feat: draft routing based on brief contact recommendation
   - WA draft si recommended_contact_method=whatsapp
   - notification si call/manual_review

5. fix: dossiers page filters by actual research existence

6. feat: pricing matrix editor in settings UI
```

---

## 7. Risks

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| Pipeline restructure rompe batch pipeline | Media | Alto | Batch pipeline usa su propio loop, no task_full_pipeline. Verificar que no comparte la chain |
| Auto-send envia sin querer | Baja (default safe) | Alto | Solo en modo "auto", y require_approved_drafts must be False |
| Contact routing genera menos drafts | Baja | Medio | Solo para leads con brief, que ya son HIGH quality |
| Race condition entre cadena principal y lateral durante migration | Media | Bajo | Idempotency guard existente previene draft duplicado |
| Tests break con nuevo dispatch pattern | Media | Bajo | Actualizar tests de pipeline dispatch |
