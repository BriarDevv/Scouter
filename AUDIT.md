# Auditoría del Proyecto ClawScout

> Generado: 2026-03-14
> Branch base: `codex/feat/wsl-linux-first`
> Estado general: 196+ tests, 11 páginas de dashboard, sistema de notificaciones, integración WhatsApp, AI workspace

---

## Resumen de Gaps

| #  | Categoría        | Gap                                      | Phase |
|----|------------------|------------------------------------------|-------|
| 1  | Infraestructura  | README.md desactualizado                 | 2     |
| 2  | Infraestructura  | No .dockerignore                         | 2     |
| 3  | Infraestructura  | Dockerfile usa python:3.12-slim          | 2     |
| 4  | Infraestructura  | No dashboard service en docker-compose   | 2     |
| 5  | Infraestructura  | dashboard/README.md es boilerplate       | 2     |
| 6  | Infraestructura  | .env.example incompleto                  | 2     |
| 7  | Operaciones      | No health service real                   | 4     |
| 8  | Operaciones      | No health strip en dashboard             | 4     |
| 9  | Operaciones      | No last_lead_at en dashboard stats       | 4     |
| 10 | Geo/Territorios  | No mapa interactivo                      | 5-6   |
| 11 | Geo/Territorios  | No modelo de territorios                 | 5-6   |
| 12 | Geo/Territorios  | No heatmap                               | 5-6   |
| 13 | Geo/Territorios  | No territorio en settings                | 5-6   |
| 14 | Geo/Territorios  | No territory summary en overview         | 5-6   |
| 15 | Testing          | No preflight script                      | 7     |
| 16 | Testing          | No WHATSAPP_DRY_RUN                      | 7     |
| 17 | Testing          | No AI workspace verification             | 7     |

---

## Detalle por Categoría

### Infraestructura (Phase 2)

**1. README.md desactualizado**
El README raíz dice Python 3.12 pero la máquina tiene 3.14. Falta documentación del dashboard, nombres de modelos incorrectos (debe decir `qwen2.5:14b`). Necesita reescritura completa con instrucciones de setup actualizadas.

**2. No .dockerignore**
No existe archivo `.dockerignore`. Sin él, `docker build` copia `node_modules/`, `.git/`, `__pycache__/` y otros directorios pesados al contexto, aumentando tiempos de build innecesariamente.

**3. Dockerfile usa python:3.12-slim**
El Dockerfile base usa `python:3.12-slim` pero el entorno de desarrollo corre Python 3.14. Esto puede causar incompatibilidades de sintaxis o dependencias. Debe actualizarse a `python:3.14-slim`.

**4. No dashboard service en docker-compose**
`docker-compose.yml` define servicios para backend (API, Celery worker, Celery beat, PostgreSQL, Redis) pero no incluye el dashboard Next.js. Para desarrollo con un solo `docker-compose up`, falta el servicio frontend.

**5. dashboard/README.md es boilerplate**
El archivo `dashboard/README.md` todavía tiene el contenido por defecto de `create-next-app`. No describe la arquitectura del dashboard, las páginas disponibles, ni cómo configurar variables de entorno del frontend.

**6. .env.example incompleto**
Faltan las siguientes variables en `.env.example`:
- `NEXT_PUBLIC_API_URL` — URL del backend para el dashboard
- `NEXT_PUBLIC_USE_REAL_API` — Toggle mock/real data
- `WHATSAPP_DRY_RUN` — Modo dry-run para desarrollo

---

### Operaciones (Phase 4)

**7. No health service real**
El endpoint `/health` retorna un JSON estático `{"status": "ok"}` sin verificar componentes. Un health check real debería validar:
- Conexión a PostgreSQL (query simple)
- Conexión a Redis (ping)
- Disponibilidad de Ollama (model list)
- Estado de Celery workers (inspect ping)

**8. No health strip en dashboard**
La página Overview del dashboard no tiene indicadores de salud del sistema. Debería mostrar el estado de cada componente (DB, Redis, Ollama, Workers) con indicadores verde/amarillo/rojo.

**9. No last_lead_at en dashboard stats**
El endpoint `/api/v1/dashboard/stats` no incluye la métrica "último lead hace X tiempo". Esta información es útil para detectar rápidamente si el pipeline de crawling dejó de funcionar.

---

### Geo / Territorios (Phase 5-6)

**10. No mapa interactivo**
Los leads tienen campos `city` y `zone` pero no existe visualización geográfica. Se necesita un componente de mapa (Leaflet o Mapbox) que muestre la distribución de leads por ubicación.

**11. No modelo de territorios**
No existe un modelo `Territory` en la base de datos que permita agrupar ciudades en territorios para análisis segmentado. Estructura sugerida: Territory -> muchas ciudades, con métricas agregadas.

**12. No heatmap**
No hay visualización de densidad o score sobre mapa. Un heatmap permitiría identificar zonas con alta concentración de leads de buen score vs zonas sin explorar.

**13. No territorio en settings**
La página de Settings no tiene una sección para gestión de territorios. Debería permitir crear/editar/eliminar territorios y asignar ciudades a cada uno.

**14. No territory summary en overview**
La página Overview no tiene una tarjeta de resumen por territorio. Debería mostrar: leads por territorio, score promedio, tasa de conversión por zona.

---

### Testing Readiness (Phase 7)

**15. No preflight script**
No existe un script automatizado que verifique requisitos antes de correr el proyecto:
- Versión de Python (>= 3.14)
- PostgreSQL accesible y con DB creada
- Redis accesible
- Ollama corriendo con modelo `qwen2.5:14b` descargado
- Migraciones de Alembic al día
- `.env` existe y tiene las variables requeridas
- `node_modules/` instalados en dashboard

**16. No WHATSAPP_DRY_RUN**
No existe un modo dry-run para el servicio de WhatsApp en desarrollo. Sin esto, las pruebas de integración podrían enviar mensajes reales por CallMeBot. Se necesita una variable `WHATSAPP_DRY_RUN=true` que loguee en vez de enviar.

**17. No AI workspace verification**
El componente `ai-workspace-section.tsx` existe en el dashboard pero los endpoints del backend que consume necesitan verificación. Hay que confirmar que los stubs responden con la estructura esperada por el frontend.

---

## Ya Resuelto en el Branch Actual

- ✅ Archivos de staging integrados (notificaciones, WhatsApp, componentes de settings)
- ✅ `settings-primitives.tsx` creado con componentes reutilizables
- ✅ AI workspace section funcional en el dashboard
- ✅ Página de Settings con 10 tabs completos
- ✅ Sistema de notificaciones (modelo, servicio, emitter, router, tests)
- ✅ Servicio de WhatsApp (proveedor CallMeBot, CRUD de credenciales)
- ✅ Página de Security
- ✅ Sidebar con badge de notificaciones

---

## Prioridad Sugerida

1. **Crítico**: Gaps 7, 15, 16 — Afectan la capacidad de operar y testear de forma segura
2. **Alto**: Gaps 1, 3, 6 — Bloquean onboarding y despliegue correcto
3. **Medio**: Gaps 2, 4, 5, 8, 9, 17 — Mejoran DX y observabilidad
4. **Bajo**: Gaps 10-14 — Features nuevos de geo/territorios, no bloquean v1
