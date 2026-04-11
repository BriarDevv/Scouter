# syntax=docker/dockerfile:1.6
#
# Multi-stage Scouter backend image.
# Stage 1 (builder) compiles wheels from the pinned-and-hashed requirements.lock
# so the runtime image never ships build-essential or libpq-dev.
# Stage 2 (runtime) carries only libpq5 + curl (for healthchecks) and runs as
# a non-root appuser.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install pinned-and-hashed dependencies first to maximize layer cache reuse.
COPY requirements.lock ./
RUN pip install --prefix=/install --require-hashes -r requirements.lock

# Install the scouter package itself (source is local) without pulling deps
# again — the lockfile already covers the full transitive set.
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN pip install --prefix=/install --no-deps .

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/usr/local/bin:$PATH

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Pull the fully-resolved site-packages + console scripts from the builder.
COPY --from=builder /install /usr/local

WORKDIR /app
COPY . .

RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --ingroup appuser appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
