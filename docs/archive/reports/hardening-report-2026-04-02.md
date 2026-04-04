# Scouter — Hardening Report + Propuesta vs Realidad

**Fecha:** 2026-04-02
**Branch:** `main`

---

## 1. Lo Que Se Hizo en Esta Corrida

### Bugs reales descubiertos en E2E con Postgres + Ollama

| Bug | Causa | Fix |
|-----|-------|-----|
| Enum uppercase en Postgres | SQLAlchemy enviaba `PENDING` en vez de `pending` | `values_callable` en todos los modelos nuevos |
| Research queue no consumida | Worker startup no listaba queue `research` | Agregada a `scouter.sh` y `docker-compose.yml` |
| Schema UUID serialization | Pydantic no serializaba UUID a string | `field_serializer` en schemas brief/research |

### Hardening implementado

| Item | Detalle |
|------|---------|
| Janitor sweepea PipelineRun | Pipelines stuck >15min se marcan failed |
| Batch pipeline con HIGH lane | research + brief inline para leads HIGH en batch |
| TOCTOU race fix | IntegrityError handling en create_or_get_report/brief |
| Research idempotency | Skip si report ya esta completed |
| correlation_id en brief chain | Parametro agregado a task_generate_brief y task_review_brief |
| LLM fallback visibility | is_fallback flag en CommercialBrief + _is_fallback en LLM client |

### E2E validado en runtime real

```
Pipeline HIGH (Taller Mecanico Los Hermanos, Mendoza):
  pipeline_dispatch  -> succeeded
  enrichment         -> succeeded
  scoring            -> succeeded (score=67, quality=high)
  analysis           -> succeeded (LLM summary + quality evaluation)
  research           -> succeeded (web=confirmed, 1 signal, description generada)
  brief_generation   -> succeeded (opp=78, tier=medium, scope=institutional_web)
  brief_review       -> succeeded (contact=call, should_call=yes)
  draft_generation   -> succeeded

Pipeline NOT-HIGH (Panaderia Don Miguel, BSAS):
  pipeline_dispatch  -> succeeded
  enrichment         -> succeeded
  scoring            -> succeeded (score=55, quality=medium)
  analysis           -> succeeded (quality=low)
  draft_generation   -> succeeded (skipped: quality low)
```

---

## 2. Propuesta vs Realidad — Comparacion Punto por Punto

### Seccion 4 de la propuesta: "Como funcionaria el producto"

| Paso propuesto | Estado real | Detalle |
|----------------|-------------|---------|
| 1. Scraper incorpora leads | **DONE** | Google Maps crawler funciona con 25 categorias |
| 2. Mote normaliza, deduplica y puntua | **DONE** | Dedup SHA-256, scoring rules-based 0-100 |
| 3. Si lead es HIGH, research | **DONE** | Pipeline bifurca en analyze, research corre para HIGH |
| 4. Playwright recolecta evidencia | **PARTIAL** | Research usa httpx (HTTP-only). Sin Playwright, sin screenshots |
| 5. Qwen 9B resume y estructura dossier | **DONE** | generate_dossier() corre inline despues de research |
| 6. Reviewer 27B revisa | **DONE** | task_review_brief valida con REVIEWER model |
| 7. Drafts mejores + demo personalizada | **PARTIAL** | Drafts condicionados por brief. Demos no implementadas (Phase 5) |
| 8. Mote deja todo listo | **DONE** | Pipeline completo, notifications wired |

### Seccion 5: High Lead Commercial Brief

| Campo propuesto | Existe? | Funciona? | Detalle |
|-----------------|---------|-----------|---------|
| budget_tier (bajo/medio/alto/premium) | SI | SI | Inferido de pricing matrix + estimated_scope |
| estimated_budget_min/max | SI | SI | Calculado desde pricing matrix configurable |
| estimated_scope | SI | SI | LLM elige entre 7 opciones |
| opportunity_score (0-100) | SI | SI | LLM genera, validado en E2E (78.0) |
| recommended_contact_method | SI | SI | Impacta draft: whatsapp prioriza WA, call/manual_review skipea draft |
| should_call | SI | SI | Validado en E2E (yes) |
| call_reason | SI | SI | LLM genera razon |
| why_this_lead_matters | SI | SI | LLM genera |
| main_business_signals | SI | SI | Lista de senales |
| main_digital_gaps | SI | SI | Lista de gaps |
| recommended_angle | SI | SI | Usado en draft generation |
| demo_recommended | SI | Parcial | Campo existe pero no dispara nada (Phase 5) |
| contact_priority | SI | SI | Inferido de opportunity_score |

### Seccion 6: Capa de investigacion con evidencia

| Capacidad propuesta | Estado | Detalle |
|--------------------|--------|---------|
| Verificar si tiene web o no | **DONE** | website_exists + website_confidence |
| Verificar si web es propia y actual | **PARTIAL** | Detecta HTTP status, no analiza contenido profundo |
| Instagram activo | **PARTIAL** | Detecta URL, no verifica actividad |
| Links salientes en bio/web | **NO** | No implementado |
| Senal de WhatsApp | **DONE** | Detecta wa.me/whatsapp en page text |
| Screenshots | **NO** | Requiere Playwright |
| HTML snapshot o metadata | **DONE** | title, description, og_tags extraidos |
| Senales detectadas | **DONE** | detected_signals_json con confidence |
| URLs encontradas | **NO** | No se extraen URLs de la pagina |
| Confianza por campo | **DONE** | website_confidence, instagram_confidence, whatsapp_confidence |

### Seccion 7: Arquitectura de agentes

| Agente propuesto | Estado | Detalle |
|------------------|--------|---------|
| Mote 8B (lider) | **DONE** | Agente con 55 tools, SSE streaming, multi-canal |
| Qwen 9B (executor) | **DONE** | Summary, quality eval, draft, dossier, brief |
| Qwen 27B (reviewer) | **DONE** | Review de leads, drafts, briefs, inbound |
| Claude Code (demos) | **NO** | Phase 5 postergada |
| Playwright (research) | **PARTIAL** | Solo httpx, no browser |

### Seccion 9: Experiencia de producto (cockpit)

| Elemento propuesto | Estado | Detalle |
|-------------------|--------|---------|
| Navegacion: Inbox | **DONE** | /responses (inbound mail) |
| Navegacion: Leads | **DONE** | /leads con tabla, detalle, export |
| Navegacion: Dossiers | **DONE** | /dossiers con research completados |
| Navegacion: Commercial Briefs | **DONE** | /briefs con lista real |
| Navegacion: Demos | **NO** | Phase 5 |
| Navegacion: Campaigns | **NO** | No implementado |
| Navegacion: Artifacts | **NO** | Modelo existe, no hay pagina |
| Navegacion: Runtime | **PARTIAL** | Toggle en ControlCenter, no pagina dedicada |
| Navegacion: Settings | **DONE** | 12 tabs incluyendo pricing matrix |
| Chat con Mote | **DONE** | Full-page + sliding panel |
| Panel derecho contextual | **PARTIAL** | Secciones colapsables en lead detail, no panel fijo |
| Runtime modes (Safe/Assisted/Auto) | **DONE** | Impacta toggles + auto-approve/send en modo auto |

### Seccion 11: Export y estructura de datos

| Capacidad propuesta | Estado | Detalle |
|--------------------|--------|---------|
| CSV/XLSX para analisis | **DONE** | /leads/export?format=csv/json/xlsx |
| JSON para agentes | **DONE** | Export JSON funcional |
| Artifacts ZIP para HIGH | **NO** | No implementado |
| Paquete exportable con dossier+brief+drafts | **NO** | Export solo de leads, no paquete completo |

### Seccion 13: Roadmap sugerido de 90 dias

| Fase propuesta | Estado |
|---------------|--------|
| Fase 1 — Dossier Engine | **DONE** (sin Playwright screenshots) |
| Fase 2 — Commercial Brief | **DONE** |
| Fase 3 — Draft Intelligence | **DONE** (drafts condicionados por brief) |
| Fase 4 — Demo Factory | **NO** (Phase 5 postergada) |
| Fase 5 — Cockpit UI | **PARTIAL** (dashboard funcional pero no es cockpit completo) |

---

## 3. Lo Que Falta Hacer

### ALTA prioridad (para operacion real)

| # | Item | Esfuerzo | Impacto |
|---|------|----------|---------|
| 1 | **Playwright browser research** — screenshots, DOM analysis, visual signals | 3-5d | Alto — propuesta depende de "evidencia visual" |
| 2 | **Export paquete HIGH** — ZIP con lead + dossier + brief + drafts | 2d | Medio — propuesta lo pide explicitamente |
| 3 | **Pagina /artifacts** — vista de screenshots/files por lead | 2d | Medio |
| 4 | **WA/TG test real** — validar con servicios reales | 1d | Alto (operacional) |

### MEDIA prioridad (para producto serio)

| # | Item | Esfuerzo | Impacto |
|---|------|----------|---------|
| 5 | Custom Prometheus counters (tasks, LLM latency) | 1d | Medio |
| 6 | Pipeline runtime dashboard / tracing view | 3d | Medio |
| 7 | Enrichment con confidence levels (no solo research) | 1d | Bajo |
| 8 | Agent memory persistente (Mote recuerda contexto) | 3-5d | Medio |
| 9 | Auto-retry de leads con LLM fallback data | 1d | Bajo |

### BAJA prioridad (nice to have)

| # | Item | Esfuerzo | Impacto |
|---|------|----------|---------|
| 10 | Pagina /campaigns | 5d | Bajo |
| 11 | Panel derecho contextual fijo en lead detail | 3d | Bajo |
| 12 | Integration tests con Postgres (Testcontainers) | 2d | Medio (testing) |

### Phase 5 (POSTERGADA)

| Item | Notas |
|------|-------|
| Demo generation (templates + Claude Code) | Requiere decisiones de arquitectura |
| demo.scouter.ai hosting | Requiere dominio + infra |
| Demo tracking (views, interactions) | Depende de demo generation |

---

## 4. Lo Que Falta Auditar

| Area | Que falta | Por que importa |
|------|-----------|-----------------|
| **UX/a11y** | Zero auditoria de accesibilidad, responsive, dark mode consistency | Producto real necesita UX audit |
| **Performance** | Zero load testing, sin benchmarks | No sabemos cuantos leads/hora procesa el pipeline |
| **Mail delivery** | Deliverability, SPF/DKIM/DMARC | Emails pueden caer en spam |
| **Seguridad red** | Reverse proxy, HTTPS, rate limiting externo | Stack expuesto solo en localhost pero falta prod config |
| **Cost tracking LLM** | Sin metricas de tokens/costo por lead | Con HIGH lane cada lead usa ~5 LLM calls |
| **Data retention** | Sin politica de limpieza de data vieja | Screenshots/artifacts van a crecer |
| **Backup/restore** | Sin strategy de backup de Postgres | Data de leads es el asset |
| **Multi-operador** | Channel router comparte conversaciones | Si hay >1 operador se mezclan |

---

## 5. Score de la Propuesta: Que Porcentaje Esta Implementado

| Seccion de la propuesta | Implementado | Nota |
|------------------------|-------------|------|
| 1. Resumen ejecutivo | 80% | Falta demos |
| 2. Problema de mercado | N/A | Contexto, no implementable |
| 3. Propuesta de valor | 75% | Sistema operativo comercial real, falta demo |
| 4. Flujo general | 85% | Pipeline completo, Playwright parcial |
| 5. Commercial Brief | 95% | Todo implementado y validado en E2E |
| 6. Investigacion con evidencia | 60% | httpx funciona, faltan screenshots/Playwright |
| 7. Arquitectura de agentes | 80% | 3 de 5 agentes activos, falta Claude Code + Playwright |
| 8. Diferencial competitivo | 70% | Investigacion + criterio + presupuesto funcionan |
| 9. Experiencia cockpit | 65% | Dashboard funcional pero no cockpit completo |
| 10. Demos y confianza | 0% | Phase 5 postergada |
| 11. Export y datos | 50% | CSV/JSON/XLSX si, ZIP paquete no |
| 12. Modelo comercial | N/A | Contexto, no implementable |
| 13. Roadmap 90 dias | 70% | 3 de 5 fases done |
| 14. Metricas | 30% | Prometheus basico, faltan metricas de negocio |
| 15. Riesgos | Activo | Principios respetados (no auto-send por default, trazabilidad) |

### **Score global: ~65-70% de la propuesta implementada y operativa.**

Lo mas valioso (Commercial Brief + pipeline HIGH + scoring + drafts condicionados) esta hecho. Lo que mas falta es la capa visual (screenshots/Playwright) y demos.
