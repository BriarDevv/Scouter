"""HTTP request context helpers and middleware."""

from __future__ import annotations

import uuid

import structlog
from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


def _normalize_or_generate(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or str(uuid.uuid4())


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = _normalize_or_generate(headers.get(REQUEST_ID_HEADER))
        correlation_id = _normalize_or_generate(headers.get(CORRELATION_ID_HEADER) or request_id)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            request_path=scope.get("path"),
            request_method=scope.get("method"),
        )

        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        state["correlation_id"] = correlation_id

        async def send_with_context(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
                response_headers[CORRELATION_ID_HEADER] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_context)
        finally:
            structlog.contextvars.clear_contextvars()
