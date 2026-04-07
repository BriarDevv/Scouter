Run the Scouter preflight check to verify all system components are ready.

Execute from the project root:
```bash
source .venv/bin/activate && python scripts/preflight.py
```

If any check fails, diagnose and report what's wrong. Common issues:
- Postgres/Redis not running → `make up` or `docker compose up -d postgres redis`
- Ollama not reachable → verify Ollama is running on Windows side
- Migrations pending → `alembic upgrade head`
- node_modules missing → `cd dashboard && npm ci`
