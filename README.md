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

## Setup en WSL (una sola vez)

Todo el desarrollo corre en WSL (Windows Subsystem for Linux). Abrir una terminal WSL:

```bash
# 1. Clonar el repo dentro de WSL (NO en /mnt/c/)
cd ~
mkdir -p src && cd src
git clone https://github.com/BriarDevv/ClawScout.git
cd ClawScout

# 2. Cambiar a la rama de desarrollo
git checkout codex/feat/wsl-linux-first

# 3. Configurar entorno
cp .env.example .env                     # Editar con tus valores (nano .env)

# 4. Backend Python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 5. Migraciones de base de datos
alembic upgrade head

# 6. Dashboard
cd dashboard && npm ci && cd ..

# 7. Modelos de Ollama (necesita Ollama corriendo)
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b

# 8. Hacer ejecutable el script de gestion
chmod +x scripts/clawscout.sh
```

> **Importante**: El repo debe vivir dentro del filesystem de WSL (ej: `~/src/ClawScout`),
> NO en `/mnt/c/...`. Correr desde el filesystem de Windows es mucho mas lento.

## Uso diario

### Encender

```bash
cd ~/src/ClawScout
make up                                  # Levanta TODO: Postgres, Redis, API, Worker, Dashboard
```

### Apagar

```bash
make down                                # Para todo (mantiene datos de Postgres/Redis)
```

### Ver estado

```bash
make status                              # Muestra que esta corriendo y en que puerto
```

### Logs

```bash
make logs                                # Todos los logs en vivo (Ctrl+C para salir)
./scripts/clawscout.sh logs api          # Solo API
./scripts/clawscout.sh logs worker       # Solo Celery worker
./scripts/clawscout.sh logs dashboard    # Solo Dashboard
```

### Todos los comandos

| Comando | Atajo | Que hace |
|---------|-------|----------|
| `make up` | `./scripts/clawscout.sh start` | Encender todo |
| `make down` | `./scripts/clawscout.sh stop` | Apagar todo (mantiene datos) |
| `make restart` | `./scripts/clawscout.sh restart` | Apagar + encender |
| `make status` | `./scripts/clawscout.sh status` | Ver estado de cada servicio |
| `make logs` | `./scripts/clawscout.sh logs` | Ver logs en vivo |
| `make preflight` | `./scripts/clawscout.sh preflight` | Verificar configuracion |
| `make seed` | `./scripts/clawscout.sh seed` | Cargar datos de prueba |
| `make nuke` | `./scripts/clawscout.sh nuke` | Parar + borrar datos (pide confirmacion) |

### Solo API + Dashboard (sin Docker ni Celery)

Si Postgres y Redis ya estan corriendo y no necesitas el worker:

```bash
make dev-up                              # Solo levanta API :8000 + Dashboard :3000
make dev-down                            # Solo para API + Dashboard
make dev-status                          # Estado de API + Dashboard
```

### Servicios disponibles (cuando esta encendido)

| Servicio | URL |
|----------|-----|
| Dashboard | http://localhost:3000 |
| API + Swagger | http://localhost:8000/docs |
| Health detallado | http://localhost:8000/health/detailed |
| Flower (opcional) | http://localhost:5555 |

### Modo manual (4 terminales)

Si preferis control individual de cada proceso:

```bash
# Terminal 1 — Infraestructura
docker compose up postgres redis

# Terminal 2 — API
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — Worker
source .venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info

# Terminal 4 — Dashboard
cd dashboard && npm run dev
```

Para apagar: `Ctrl+C` en cada terminal + `docker compose down`.

### Docker Compose completo (alternativa)

```bash
docker compose up -d                     # Levanta todo en containers
docker compose logs -f                   # Ver logs
docker compose down                      # Apagar
```

## Que es automatico y que es manual

En ClawScout v1, **casi todo es manual**. No hay tareas programadas, no hay
auto-crawl, no hay Celery Beat. Todo se dispara cuando vos lo pedis.

| Componente | Automatico? | Como se controla |
|---|---|---|
| Crawlers | No — se corren a mano | Nada que apagar |
| Enrichment / Scoring / Drafts | No — se disparan por API | Nada que apagar |
| Reviewer (modelo 27b) | No — vos lo pedis | Nada que apagar |
| Reply assistant | Toggle en Settings | `reply_assistant_enabled` |
| Auto-classify inbound | Toggle en Settings | `auto_classify_inbound` |
| Reviewer automatico | Toggle en Settings | `reviewer_enabled` |
| Mail inbound sync | Toggle en Settings | `mail_inbound_sync_enabled` |
| WhatsApp alerts | Toggle en Settings | `whatsapp_alerts_enabled` |
| OpenClaw | Proceso separado | No se toca con make up/down |

Los modelos de Ollama (4b, 9b, 27b) solo consumen VRAM cuando los usas.
Ollama los descarga de memoria automaticamente despues de unos minutos de
inactividad.

### Modo "solo OpenClaw" (estacionar el sistema)

Si queres dejar solo OpenClaw funcionando y apagar todo lo demas:

```bash
make down                                # Apaga API, Worker, Dashboard, Postgres, Redis
```

OpenClaw sigue funcionando porque es un proceso independiente.
Cuando quieras volver: `make up`.

### Apagar features de IA sin apagar el sistema

Desde el dashboard en **Settings > Reglas**, podes desactivar:
- **Reply assistant** — genera respuestas automaticas a emails entrantes
- **Reviewer** — revisa automaticamente drafts y mensajes
- **Auto-classify inbound** — clasifica emails entrantes con IA

Todos estos toggles estan en `false` por default, asi que la IA automatica
no corre salvo que la enciendas explicitamente.

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
