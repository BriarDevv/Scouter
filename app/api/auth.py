"""API Key authentication middleware.

When API_KEY is set in config, all requests to /api/v1/* must include
the X-API-Key header (except webhooks and health endpoints).
When API_KEY is None (development), auth is disabled.
"""

import hmac

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Paths that never require authentication
_PUBLIC_PREFIXES = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)

# Webhook paths use their own auth (header secret validation)
_WEBHOOK_PATHS = (
    "/api/v1/whatsapp/webhook",
    "/api/v1/telegram/webhook",
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth if API_KEY not configured (development mode)
        if not settings.API_KEY:
            return await call_next(request)

        path = request.url.path

        # Skip public endpoints
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # Skip webhook endpoints (they have their own auth)
        if any(path.startswith(p) for p in _WEBHOOK_PATHS):
            return await call_next(request)

        # Skip CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check API key
        provided = request.headers.get("X-API-Key", "")
        if not provided or not hmac.compare_digest(provided, settings.API_KEY):
            return JSONResponse(
                status_code=401,
                content={"detail": "API key inválida o faltante."},
            )

        return await call_next(request)
