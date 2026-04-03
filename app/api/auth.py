"""API Key authentication middleware.

When API_KEY is set in config, all requests to /api/v1/* must include
the X-API-Key header (except webhooks and health endpoints).
When API_KEY is None (development), auth is disabled.
"""

import hmac

from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

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


class APIKeyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip auth if API_KEY not configured (development mode)
        if not settings.API_KEY:
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]

        # Skip public endpoints
        if any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            await self.app(scope, receive, send)
            return

        # Skip webhook endpoints (they have their own auth)
        if any(path.startswith(p) for p in _WEBHOOK_PATHS):
            await self.app(scope, receive, send)
            return

        # Skip CORS preflight
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Check API key
        headers = Headers(scope=scope)
        provided = headers.get("X-API-Key", "")
        if not provided or not hmac.compare_digest(provided, settings.API_KEY):
            response = JSONResponse(
                status_code=401,
                content={"detail": "API key inválida o faltante."},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
