# Scouter Installation from Scratch

Everything runs inside **WSL** (Windows Subsystem for Linux). The repo **must** live
in the WSL filesystem (e.g. `~/src/Scouter`), **not** in `/mnt/c/...`.

## Prerequisites

### 1. WSL2 + Ubuntu

Open **PowerShell as Administrator**:

```powershell
wsl --install -d Ubuntu
```

Restart if prompted. Then in Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl git
```

### 2. Docker Desktop

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Enable **"Use WSL 2 based engine"**
3. Settings -> Resources -> WSL Integration -> Enable your Ubuntu distro
4. Apply & Restart

Verify: `docker --version && docker compose version`

### 3. Ollama

Install on **Windows** (uses GPU directly): [ollama.com/download](https://ollama.com/download)

Verify from WSL: `curl -s http://localhost:11434/api/tags | head -c 100`

### 4. Python 3.12+ and Node.js v24+

```bash
# Python
python3 --version  # Should be 3.12+
# If not: sudo apt install -y python3 python3-pip python3-venv

# Node via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 24 && nvm use 24
```

## Setup

### Automated (recommended)

```bash
git clone https://github.com/BriarDevv/Scouter.git ~/src/Scouter
cd ~/src/Scouter
bash scripts/init.sh
```

The init script handles: venv, pip deps, npm deps, .env creation, Docker infra, DB migrations, and Ollama model downloads.

### Manual

```bash
cd ~/src/Scouter

cp .env.example .env                     # Edit: nano .env
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

docker compose up -d postgres redis
alembic upgrade head

cd dashboard && npm ci && cd ..

ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
ollama pull qwen3.5:27b
ollama pull hermes3:8b

chmod +x scripts/scouter.sh
```

## First Run

```bash
make up
```

Open http://localhost:3000 — the onboarding wizard guides you through:
1. Runtime check (Postgres, Redis, Ollama)
2. Brand & signature setup
3. Outreach channel (WhatsApp or Email)
4. Optional: Telegram notifications

## Manual Mode (4 terminals)

```bash
# T1: docker compose up postgres redis
# T2: source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# T3: source .venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info
# T4: cd dashboard && npm run dev
```

## LLM Models

| Role | Model | Env Override |
| --- | --- | --- |
| Leader | qwen3.5:4b | `OLLAMA_LEADER_MODEL` |
| Executor | qwen3.5:9b | `OLLAMA_EXECUTOR_MODEL` |
| Reviewer | qwen3.5:27b | `OLLAMA_REVIEWER_MODEL` |
| Agent (Mote) | hermes3:8b | — |

Models auto-unload from VRAM after inactivity. LOW_RESOURCE_MODE (Settings > Rules) forces sequential loading for machines with <= 16GB RAM.

## Troubleshooting

See [local-dev-wsl.md](local-dev-wsl.md) for WSL-specific workflow and common issues.
