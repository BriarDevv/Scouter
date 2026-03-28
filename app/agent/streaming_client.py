"""Async streaming client for Ollama chat completions."""

import json
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentStreamError(Exception):
    """Error during agent streaming."""

    pass


async def stream_ollama_chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.4,
    num_predict: int = 4096,
    timeout: float = 180.0,
) -> AsyncGenerator[str, None]:
    """Stream tokens from Ollama /api/chat.

    Ollama with stream=True returns NDJSON — one JSON object per line:
    {"message": {"content": "token"}, "done": false}
    ...
    {"message": {"content": ""}, "done": true}

    Yields individual content strings as they arrive.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": 16384,
        },
    }

    logger.debug(
        "agent_stream_request",
        model=model,
        message_count=len(messages),
        timeout=timeout,
    )

    try:
        async with (
            httpx.AsyncClient(timeout=timeout) as client,
            client.stream("POST", url, json=payload) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if chunk.get("done"):
                    break
                content = chunk.get("message", {}).get("content", "")
                if content:
                    yield content
    except httpx.TimeoutException as exc:
        logger.error("agent_stream_timeout", model=model, error=str(exc))
        raise AgentStreamError(
            f"Ollama streaming timeout after {timeout}s"
        ) from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "agent_stream_http_error",
            model=model,
            status=exc.response.status_code,
        )
        raise AgentStreamError(
            f"Ollama HTTP error: {exc.response.status_code}"
        ) from exc
    except httpx.ConnectError as exc:
        logger.error("agent_stream_connect_error", model=model)
        raise AgentStreamError("No se pudo conectar a Ollama") from exc
