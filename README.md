# ClawScout

Sistema privado de prospeccion de leads para servicios de desarrollo web.
Detecta negocios que necesitan desarrollo/rediseno web, enriquece leads, los puntua, genera borradores de contacto y soporta revision humana antes del envio.

## Stack

| Capa | Tecnologia |
|------|-----------|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.x, Celery, structlog |
| Base de datos | PostgreSQL 16, Redis 7 |
| LLM | Ollama — catalogo: `qwen3.5:4b`, `qwen3.5:9b`, `qwen3.5:27b` |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui (base-ui) |
| Infra | Docker Compose, Alembic (migraciones) |

## Mapa de servicios

| Servicio | Puerto | Descripcion |
|----------|--------|-------------|
| API | `:8000` | FastAPI backend (Swagger en `/docs`) |
| Dashboard | `:3000` | Next.js frontend |
| Flower | `:5555` | Monitor de Celery |
| PostgreSQL | `:5432` | Base de datos principal |
| Redis | `:6379` | Broker de Celery + cache |

## Prerequisitos

- Python 3.14+
- Node.js v24+
- Docker + Docker Compose
- Ollama (para funciones LLM)

## Instalacion (una sola vez)

```bash
# 1. Clonar y configurar
git clone <repo-url> && cd ClawScout
cp .env.example .env                     # Editar con tus valores

# 2. Backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Dashboard
cd dashboard && npm ci && cd ..

# 4. Modelos de Ollama
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
```

## Encender el sistema

### Opcion A: Desarrollo local (recomendado)

Abrir 4 terminales en WSL:

```bash
# Terminal 1 — Infraestructura (Postgres + Redis)
docker compose up postgres redis

# Terminal 2 — API backend
source .venv/bin/activate
alembic upgrade head                     # Solo la primera vez o si hay migraciones nuevas
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — Worker de Celery (procesa tareas async)
source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# Terminal 4 — Dashboard frontend
cd dashboard
npm run dev
```

Servicios disponibles:
- API + Swagger: http://localhost:8000/docs
- Dashboard: http://localhost:3000
- Health check: http://localhost:8000/health
- Health detallado: http://localhost:8000/health/detailed

**Opcional** — Monitor de Celery (Flower):
```bash
# Terminal 5
source .venv/bin/activate
celery -A app.workers.celery_app flower --port=5555
# Flower: http://localhost:5555
```

**Opcional** — Preflight (verificar que todo este listo):
```bash
source .venv/bin/activate
python scripts/preflight.py
```

### Opcion B: Docker Compose completo

```bash
cp .env.example .env                     # Si no existe
docker compose up -d                     # Levanta todo: postgres, redis, api, worker, flower, dashboard
docker compose logs -f                   # Ver logs en tiempo real
```

Servicios: mismos puertos que arriba.

## Apagar el sistema

### Desarrollo local

```bash
# Ctrl+C en cada terminal, o desde cualquier terminal:
# Parar infraestructura Docker
docker compose down                      # Mantiene los datos
docker compose down -v                   # Borra volumenes (datos de postgres/redis)
```

### Docker Compose completo

```bash
docker compose down                      # Parar todo, mantener datos
docker compose down -v                   # Parar todo y borrar datos
```

## Seedear datos de prueba

```bash
source .venv/bin/activate
python scripts/seed.py                   # Crea leads de ejemplo + territorios
```

## Configuracion de LLM

El sistema usa Ollama con modelos qwen3.5 asignados por rol:

| Rol | Modelo default | Variable de entorno |
|-----|---------------|---------------------|
| Leader | `qwen3.5:4b` | `OLLAMA_LEADER_MODEL` |
| Executor | `qwen3.5:9b` | `OLLAMA_EXECUTOR_MODEL` |
| Reviewer | `qwen3.5:27b` | `OLLAMA_REVIEWER_MODEL` |

```bash
# Descargar los modelos necesarios
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
```

El catalogo de modelos soportados se configura con `OLLAMA_SUPPORTED_MODELS` en `.env`.
La variable legacy `OLLAMA_MODEL` sigue funcionando como fallback para el rol executor.

## Estructura del proyecto

```
ClawScout/
|-- app/                      # Backend Python
|   |-- api/v1/               # Endpoints FastAPI
|   |-- core/                 # Config (pydantic-settings), logging (structlog)
|   |-- db/                   # Session factory, Base model
|   |-- models/               # SQLAlchemy models
|   |-- schemas/              # Pydantic request/response schemas
|   |-- services/             # Business logic layer
|   |-- workers/              # Celery app + tasks
|   |-- llm/                  # Ollama client, catalogo, roles, prompts
|   |-- mail/                 # Email send/receive
|   |-- scoring/              # Motor de scoring basado en reglas
|   |-- outreach/             # Generacion de borradores via LLM
|   |-- crawlers/             # BaseCrawler ABC + implementaciones
|-- dashboard/                # Frontend Next.js 16
|   |-- app/                  # App Router -- paginas
|   |-- components/           # UI, shared, charts, layout
|   |-- lib/                  # API client, hooks, constants
|   |-- data/                 # Mock data para desarrollo
|   |-- types/                # TypeScript definitions
|-- alembic/                  # Migraciones de base de datos
|-- infra/                    # Dockerfiles, config de infra
|-- scripts/                  # Scripts utilitarios
|-- tests/                    # Tests del backend
|-- docker-compose.yml        # Orquestacion de servicios
|-- pyproject.toml            # Config del proyecto Python
|-- .env.example              # Template de variables de entorno
```

## Paginas del dashboard

| Pagina | Ruta | Descripcion |
|--------|------|-------------|
| Overview | `/` | Metricas generales, pipeline visual, graficos temporales |
| Leads | `/leads` | Tabla paginada con filtros, busqueda y acciones |
| Lead Detail | `/leads/[id]` | Senales detectadas, score, drafts, timeline |
| Outreach | `/outreach` | Gestion de borradores: pendientes, aprobados, enviados |
| Performance | `/performance` | Metricas por industria, ciudad y fuente |
| Suppression | `/suppression` | Lista de supresion global |
| Responses | `/responses` | Respuestas inbound clasificadas por LLM |
| Activity | `/activity` | Log de actividad del sistema |
| Notifications | `/notifications` | Notificaciones y alertas |
| Security | `/security` | Configuracion de seguridad |
| Settings | `/settings` | Configuracion general del sistema |

## Endpoints de la API

Swagger interactivo en `http://localhost:8000/docs`.

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/leads` | Crear lead |
| GET | `/api/v1/leads` | Listar leads (paginado, filtrable) |
| GET | `/api/v1/leads/{id}` | Obtener lead con senales |
| POST | `/api/v1/enrichment/{id}` | Enriquecer lead (sync) |
| POST | `/api/v1/enrichment/{id}/async` | Enriquecer lead (async) |
| POST | `/api/v1/scoring/{id}` | Puntuar lead |
| POST | `/api/v1/scoring/{id}/analyze` | Analisis LLM (async) |
| POST | `/api/v1/scoring/{id}/pipeline` | Pipeline completo (async) |
| POST | `/api/v1/outreach/{id}/draft` | Generar borrador de contacto |
| GET | `/api/v1/outreach/drafts` | Listar borradores |
| POST | `/api/v1/outreach/drafts/{id}/review` | Aprobar/rechazar borrador |
| POST | `/api/v1/suppression` | Agregar a lista de supresion |
| GET | `/api/v1/suppression` | Listar supresiones |
| DELETE | `/api/v1/suppression/{id}` | Eliminar de supresion |

## Pipeline de prospeccion

```
1. Ingesta de lead (manual o crawler)
2. Enriquecimiento: analizar website, detectar senales
3. Scoring: puntuacion basada en reglas desde senales
4. Analisis LLM: resumen, evaluacion de calidad, angulo sugerido
5. Generacion de borrador de contacto
6. Revision humana: aprobar / rechazar
7. Envio (v2)
```

## Tests

```bash
# Backend (pytest con SQLite)
pytest -v

# Frontend (type checking)
cd dashboard && npx tsc --noEmit
```

Los tests del backend usan SQLite via override en `conftest.py` para aislamiento.

## Variables de entorno

Copiar `.env.example` a `.env` y completar los valores.
Ver `.env.example` para la lista completa de variables disponibles.

## Decisiones de diseno

- **Celery sobre RQ**: Retries nativos, routing por queue, rate limiting por tarea, Flower para monitoreo.
- **SQLAlchemy sync para v1**: Mas simple, FastAPI lo soporta bien. Migracion a async es directa con SQLAlchemy 2.x.
- **structlog**: Logs estructurados en JSON para auditoria y debugging.
- **Dedup via hash**: SHA-256 de (business_name + city + domain) normalizado. Previene duplicados en insert.
- **Supresion global**: Se verifica al crear leads, antes de generar outreach, y en operaciones bulk.
- **Output LLM como untrusted**: Extraccion JSON con fallback, outputs sanitizados antes de guardar.
- **Sin auto-send en v1**: Todo outreach requiere aprobacion humana.
- **shadcn/ui con base-ui**: Usa prop `render` en vez de `asChild` (no Radix).
- **Tailwind v4**: Config inline con `@theme`, sin `tailwind.config.ts`.
