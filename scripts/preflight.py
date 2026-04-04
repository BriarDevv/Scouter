#!/usr/bin/env python3
"""Scouter Preflight Check — verifica que todos los componentes esten listos."""

import os
import sys
import subprocess
import importlib
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

CHECKS_PASSED = 0
CHECKS_FAILED = 0
CHECKS_WARNED = 0


def ok(msg: str):
    global CHECKS_PASSED
    CHECKS_PASSED += 1
    print(f"  {GREEN}\u2705 {msg}{RESET}")


def fail(msg: str):
    global CHECKS_FAILED
    CHECKS_FAILED += 1
    print(f"  {RED}\u274c {msg}{RESET}")


def warn(msg: str):
    global CHECKS_WARNED
    CHECKS_WARNED += 1
    print(f"  {YELLOW}\u26a0\ufe0f  {msg}{RESET}")


def load_env() -> dict[str, str]:
    """Load .env file manually (no external deps)."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env_vars: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def check_python():
    v = sys.version_info
    version_str = f"{v.major}.{v.minor}.{v.micro}"
    if v.major == 3 and v.minor >= 12:
        ok(f"Python {version_str}")
    else:
        fail(f"Python {version_str} (se requiere >= 3.12)")


def check_postgres(env: dict[str, str]):
    db_url = env.get("DATABASE_URL", "")
    if not db_url:
        fail("PostgreSQL: DATABASE_URL no configurada en .env")
        return
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        host = db_url.split("@")[-1].split("/")[0] if "@" in db_url else "desconocido"
        ok(f"PostgreSQL conectado ({host})")
    except Exception as e:
        fail(f"PostgreSQL no disponible: {e}")


def check_redis(env: dict[str, str]):
    redis_url = env.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as r
        client = r.Redis.from_url(redis_url, socket_connect_timeout=3)
        client.ping()
        client.close()
        ok(f"Redis conectado ({redis_url.split('@')[-1] if '@' in redis_url else redis_url})")
    except ImportError:
        warn("Redis: paquete 'redis' no instalado")
    except Exception as e:
        fail(f"Redis no disponible: {e}")


def check_ollama(env: dict[str, str]):
    base_url = env.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import httpx
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            model_name = env.get("OLLAMA_MODEL", "")
            if model_name and not any(model_name in m for m in models):
                warn(f"Ollama disponible pero modelo '{model_name}' no encontrado")
                return
            ok(f"Ollama disponible ({len(models)} modelo{'s' if len(models) != 1 else ''})")
        else:
            fail(f"Ollama respondio HTTP {resp.status_code}")
    except ImportError:
        warn("Ollama: paquete 'httpx' no instalado")
    except Exception as e:
        fail(f"Ollama no disponible: {e}")


def check_migrations():
    try:
        result = subprocess.run(
            ["alembic", "check"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if result.returncode == 0:
            ok("Migraciones al dia")
        else:
            warn(f"Migraciones: {result.stderr.strip()[:100]}")
    except FileNotFoundError:
        warn("Alembic no encontrado en PATH")
    except Exception as e:
        warn(f"Migraciones: {e}")


def check_env_file():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        lines = [l for l in env_path.read_text().splitlines() if l.strip() and not l.strip().startswith("#")]
        ok(f".env presente ({len(lines)} variables)")
    else:
        fail(".env no existe (copiar de .env.example)")


def check_node():
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        version = result.stdout.strip()
        ok(f"Node.js {version}")
    except FileNotFoundError:
        fail("Node.js no encontrado")
    except Exception as e:
        fail(f"Node.js: {e}")


def check_node_modules():
    nm_path = Path(__file__).resolve().parent.parent / "dashboard" / "node_modules"
    if nm_path.exists():
        ok("node_modules instalados")
    else:
        warn("node_modules no instalados (ejecutar: cd dashboard && npm install)")


def check_python_packages():
    required = ["fastapi", "sqlalchemy", "celery", "structlog", "pydantic", "httpx"]
    missing = []
    for pkg in required:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    if not missing:
        ok("Paquetes Python OK")
    else:
        fail(f"Paquetes Python faltantes: {', '.join(missing)}")


def check_dashboard_build():
    next_path = Path(__file__).resolve().parent.parent / "dashboard" / ".next"
    if next_path.exists():
        ok("Dashboard buildeado (.next existe)")
    else:
        warn("Dashboard no buildeado (.next no existe)")


def main():
    print(f"\n{BOLD}\U0001f50d Scouter Preflight Check{RESET}")
    print("\u2550" * 40)
    print()

    env = load_env()

    check_python()
    check_postgres(env)
    check_redis(env)
    check_ollama(env)
    check_migrations()
    check_env_file()
    check_node()
    check_node_modules()
    check_python_packages()
    check_dashboard_build()

    total = CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNED
    print()
    print("\u2550" * 40)
    print(f"  Resultado: {GREEN}{CHECKS_PASSED}{RESET}/{total} checks pasaron")
    if CHECKS_WARNED:
        print(f"  {YELLOW}\u26a0\ufe0f  {CHECKS_WARNED} warning{'s' if CHECKS_WARNED != 1 else ''}{RESET}")
    if CHECKS_FAILED:
        print(f"  {RED}\u274c {CHECKS_FAILED} error{'es' if CHECKS_FAILED != 1 else ''}{RESET}")
    print()

    sys.exit(1 if CHECKS_FAILED > 0 else 0)


if __name__ == "__main__":
    main()
