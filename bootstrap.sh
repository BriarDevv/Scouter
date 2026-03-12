#!/usr/bin/env bash
set -euo pipefail
DEFAULT_OLLAMA_MODEL="qwen3.5:9b"

echo "=== ClawScout v1 — Bootstrap (Linux/WSL) ==="

# Check Python version
python3 --version 2>/dev/null || { echo "ERROR: Python 3 not found"; exit 1; }

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# Copy .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "IMPORTANT: Edit .env with your actual values before running."
fi

# Start infrastructure
echo "Starting PostgreSQL and Redis via Docker Compose..."
docker compose up -d postgres redis

# Wait for PostgreSQL
echo "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
    if docker compose exec postgres pg_isready -U clawscout > /dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    sleep 1
done

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Pull Ollama model (if ollama is installed)
if command -v ollama &> /dev/null; then
    echo "Pulling default Ollama model via Ollama (${DEFAULT_OLLAMA_MODEL})..."
    ollama pull "${DEFAULT_OLLAMA_MODEL}"
else
    echo "NOTE: Ollama not found. Install it from https://ollama.ai and run: ollama pull ${DEFAULT_OLLAMA_MODEL}"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Commands:"
echo "  uvicorn app.main:app --reload          # Start API server"
echo "  celery -A app.workers.celery_app worker --loglevel=info  # Start worker"
echo "  pytest                                  # Run tests"
echo "  docker compose up -d                    # Start all services"
echo ""
