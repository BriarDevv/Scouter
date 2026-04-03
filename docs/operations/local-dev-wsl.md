# ClawScout Linux-First Local Workflow

Validated on WSL2 / Ubuntu with the repo cloned into `~/src/ClawScout`.

## A. Arquitectura operativa actual

| Componente | Rol actual | Dónde corre hoy | Estado |
|---|---|---|---|
| ClawScout core | Source of truth del sistema | WSL / repo Linux-native | Validado |
| FastAPI backend | API + contratos + tracking | WSL | Validado |
| Celery worker | Async tasks + pipeline | WSL | Validado |
| PostgreSQL | Persistencia principal | Docker Desktop | Validado desde WSL |
| Redis | Broker / backend Celery | Docker Desktop | Validado desde WSL |
| Ollama | Runtime LLM | Windows, expuesto a WSL | Validado |
| Dashboard Next.js | UI operativa | WSL | Validado |
| Playwright / Chromium | Runtime browser local | WSL | Validado |
| Task tracking | `task_runs` + `pipeline_runs` | PostgreSQL + API | Validado |
| Pipeline | enrich -> score -> analyze -> draft | API + worker + LLM | Validado E2E |

## B. Entorno actual recomendado

- Entorno principal: **WSL2 / Ubuntu**
- Repo principal: `~/src/ClawScout`
- Rama principal: `main` (migrado desde `codex/feat/wsl-linux-first` el 2026-03-27)
- El clon Windows ya no se usa como fallback
- Windows sigue usándose de forma temporal para:
  - Docker Desktop
  - instancia dedicada de Ollama accesible desde WSL

## C. Comandos de arranque

### 0. Preparación guiada del stack local

Para validar prerequisitos y obtener los comandos exactos de arranque:

```bash
cd ~/src/ClawScout
./scripts/start-local-stack.sh
```

Si querés que además intente levantar servicios en `tmux` sin duplicar procesos ya vivos:

```bash
cd ~/src/ClawScout
./scripts/start-local-stack.sh --launch
```

También acepta selección puntual:

```bash
./scripts/start-local-stack.sh --launch --service backend --service worker
```

### 1. Infraestructura base

Estado validado actual:

- PostgreSQL y Redis siguen en Docker Desktop
- Backend, worker y dashboard corren en WSL

Si Docker Desktop ya tiene integración con Ubuntu, desde WSL:

```bash
cd ~/src/ClawScout
docker compose up -d postgres redis
```

Si Docker sigue estando solo del lado Windows, usar PowerShell:

```powershell
docker compose -f C:\Users\mateo\Desktop\ClawScout\docker-compose.yml up -d postgres redis
```

### 2. Backend

```bash
cd ~/src/ClawScout
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Worker

Pool validado para Linux / WSL: `prefork`

```bash
cd ~/src/ClawScout
source .venv/bin/activate
celery -A app.workers.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --pool=prefork \
  --queues=default,enrichment,scoring,llm,reviewer \
  --hostname=clawscout-wsl
```

### 4. Dashboard

```bash
cd ~/src/ClawScout/dashboard
npm ci
npm run dev -- --hostname 0.0.0.0 --port 3000
```

### 5. Salud y smoke checks

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/dashboard/stats
curl http://127.0.0.1:8000/api/v1/pipelines/runs
curl http://127.0.0.1:8000/api/v1/tasks/<task_id>/status
curl -I http://127.0.0.1:3000
```

### 6. Tests

```bash
cd ~/src/ClawScout
source .venv/bin/activate
pytest -q
```

### 7. Task status y pipeline tracking

```bash
curl http://127.0.0.1:8000/api/v1/tasks/<task_id>/status
curl http://127.0.0.1:8000/api/v1/tasks?lead_id=<lead_id>
curl http://127.0.0.1:8000/api/v1/pipelines/runs?lead_id=<lead_id>
curl http://127.0.0.1:8000/api/v1/pipelines/runs/<pipeline_run_id>
```

## D. Dependencias operativas

### Python / backend

- Python `3.12`
- virtualenv Linux en `~/src/ClawScout/.venv`
- instalación base:

```bash
pip install -e ".[dev]"
```

### Node / dashboard

- Node `>=20.9.0`
- npm Linux-native
- validado con:
  - `node v20.20.1`
  - `npm 10.8.2`

### Playwright

```bash
cd ~/src/ClawScout
source .venv/bin/activate
pip install -e ".[playwright]"
python -m playwright install-deps chromium
python -m playwright install chromium
```

### Docker Desktop

- sigue siendo la forma validada de correr PostgreSQL y Redis localmente
- WSL consume esos puertos por `localhost`

### Ollama

- modelo default real: `qwen3.5:9b`
- catálogo preparado:
  - `qwen3.5:4b`
  - `qwen3.5:9b`
  - `qwen3.5:27b`

### Variables de entorno relevantes

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_SUPPORTED_MODELS`
- `API_CORS_ORIGINS`
- `NEXT_PUBLIC_API_URL`

## E. Notas importantes de integración

### Ollama desde WSL

Solución validada hoy:

- Ollama sigue en Windows
- WSL consume una instancia dedicada expuesta al bridge WSL
- `OLLAMA_BASE_URL` del clon Linux apunta a esa instancia
- El bridge se restaura con:

```bash
cd ~/src/ClawScout
bash scripts/ensure-ollama-bridge.sh
```

- Para imprimir solo la URL efectiva del bridge:

```bash
bash scripts/ensure-ollama-bridge.sh --print-url
```

Ejemplo validado:

```env
OLLAMA_BASE_URL=http://172.22.48.1:11435
OLLAMA_MODEL=qwen3.5:9b
```

Importante:

- la IP del bridge WSL puede cambiar tras reinicios de WSL o de red
- el helper detecta la gateway actual desde `ip route show default` y relanza una segunda instancia de Ollama atada a esa IP
- si el `.env` local de ClawScout sigue apuntando a una URL vieja, actualizar `OLLAMA_BASE_URL`
- esto es **temporal y reversible** hasta decidir si Ollama migra a WSL

### CORS dashboard -> backend

Se resolvió con:

```env
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Eso cubre el dev server de Next tanto en `localhost` como en `127.0.0.1`.

### DNS / TLS en WSL

Estado validado:

- `generateResolvConf=false` en `/etc/wsl.conf`
- `/etc/resolv.conf` gestionado manualmente con resolvers públicos
- `SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt` en `~/.profile`

Esto permitió estabilizar:

- resolución DNS externa
- `curl`
- `httpx`
- enrichment HTTP real
- Playwright

Estos cambios son **del entorno**, no del repo, y son reversibles.

## F. Troubleshooting corto

### Docker no levantó

- Confirmar que Docker Desktop esté abierto en Windows
- Verificar puertos desde WSL:

```bash
nc -zv 127.0.0.1 5432
nc -zv 127.0.0.1 6379
```

### Ollama no responde

- Restaurar el bridge WSL -> Windows:

```bash
cd ~/src/ClawScout
bash scripts/ensure-ollama-bridge.sh
```

- Comprobar desde WSL:

```bash
curl "$OLLAMA_BASE_URL/api/tags"
```

- Si falla tras reinicio de WSL, el helper vuelve a detectar la IP del gateway actual y relanza la instancia dedicada

### DNS falla

- Revisar `/etc/wsl.conf`
- Revisar `/etc/resolv.conf`
- Reiniciar la distro:

```powershell
wsl --terminate Ubuntu
```

### Dashboard cae a mocks

- Verificar backend:

```bash
curl http://127.0.0.1:8000/health
```

- Verificar CORS:
  - `API_CORS_ORIGINS`
  - origen real del dashboard (`localhost:3000` o `127.0.0.1:3000`)

### CORS

- Si el navegador muestra errores de `fetch` bloqueado:
  - backend no tomó la config nueva
  - el origen de la UI no está en `API_CORS_ORIGINS`
  - reiniciar `uvicorn`

### Node version

- Next 16 requiere `Node >=20.9.0`
- Validar:

```bash
node -v
npm -v
which node
```

### Playwright / browser issues

- Reinstalar deps del sistema:

```bash
python -m playwright install-deps chromium
python -m playwright install chromium
```

- Si la navegación falla, revisar primero DNS/TLS y no solo Playwright

## G. Estado validado

### 100% probado en Linux-first

- backend FastAPI en WSL
- worker Celery en WSL
- PostgreSQL y Redis consumidos desde WSL
- Ollama consumido desde WSL
- DNS/TLS/HTTP externo estables
- Playwright / Chromium headless
- dashboard Next.js en WSL
- pantallas del dashboard ya conectadas a backend real:
  - overview
  - leads
  - lead detail
  - outreach
  - performance
  - suppression
- task status API
- pipeline runs persistidos
- dashboard consumiendo backend real
- flujo E2E:
  - create lead
  - enrich async
  - score/analyze
  - full pipeline
  - draft generation
  - dashboard lead detail con tracking

### Pendiente

- settings / model selection por rol
- página `settings` todavía esencialmente estática
- mover Ollama fuera de Windows si deja de ser conveniente
- activar Docker integration directa dentro de Ubuntu, si se quiere cerrar también ese frente
- crawler Playwright real más allá del runtime validado
- channels reales de outbound

### Warnings no bloqueantes actuales

- warnings de Recharts en `next dev` sobre `width(-1)` / `height(-1)`
- el lead list puede truncar nombres largos por diseño visual
- la IP del bridge WSL usada por Ollama es temporal y puede cambiar

## H. Próximos pasos

No implementados todavía. Roadmap corto sugerido:

1. **Model selection por rol**
   - separar leader / executor / fallback models
   - conservar `qwen3.5:9b` como default operativo hasta que exista routing claro

2. **Hermes líder**
   - montar la capa líder de Hermes sobre el backend actual
   - mantener ClawScout como source of truth

3. **Tools / canales**
   - navegador: pasar del runtime Playwright validado a tools/crawlers reales
   - mail: aprobación humana + envío controlado
   - WhatsApp: canal separado, no mezclarlo con email desde el inicio

4. **Supervisor / múltiples executors**
   - agregar supervisor solo cuando ya exista routing y observabilidad suficiente
   - preparar múltiples executors sin romper el backend actual
