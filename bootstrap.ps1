# ClawScout v1 — Bootstrap (Windows PowerShell)
$ErrorActionPreference = "Stop"
$defaultOllamaModel = "qwen3.5:9b"

Write-Host "=== ClawScout v1 — Bootstrap (Windows) ===" -ForegroundColor Cyan

# Check Python
try {
    python --version
} catch {
    Write-Host "ERROR: Python not found. Install Python 3.12+ from python.org" -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install -e ".[dev]"

# Copy .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item .env.example .env
    Write-Host "IMPORTANT: Edit .env with your actual values before running." -ForegroundColor Yellow
}

# Start infrastructure
Write-Host "Starting PostgreSQL and Redis via Docker Compose..."
docker compose up -d postgres redis

# Wait for PostgreSQL
Write-Host "Waiting for PostgreSQL..."
for ($i = 0; $i -lt 30; $i++) {
    $result = docker compose exec postgres pg_isready -U clawscout 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PostgreSQL is ready."
        break
    }
    Start-Sleep -Seconds 1
}

# Run migrations
Write-Host "Running database migrations..."
alembic upgrade head

# Check for Ollama
$ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaPath) {
    Write-Host "Pulling default Ollama model via Ollama ($defaultOllamaModel)..."
    ollama pull $defaultOllamaModel
} else {
    Write-Host "NOTE: Ollama not found. Install from https://ollama.ai and run: ollama pull $defaultOllamaModel" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Commands:"
Write-Host "  uvicorn app.main:app --reload          # Start API server"
Write-Host "  celery -A app.workers.celery_app worker --loglevel=info  # Start worker"
Write-Host "  pytest                                  # Run tests"
Write-Host "  docker compose up -d                    # Start all services"
Write-Host ""
