#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_TIMEOUT_SECONDS = 20.0


@dataclass(frozen=True)
class CommandSpec:
    method: str
    path_template: str
    mutating: bool = False


COMMAND_SPECS: dict[str, CommandSpec] = {
    "recent-drafts": CommandSpec("GET", "/outreach/drafts"),
    "draft-detail": CommandSpec("GET", "/outreach/drafts/{draft_id}"),
    "send-status": CommandSpec("GET", "/outreach/drafts/{draft_id}/deliveries"),
    "send-draft": CommandSpec("POST", "/outreach/drafts/{draft_id}/send", mutating=True),
}


class APIClientError(RuntimeError):
    def __init__(self, response: dict[str, Any], exit_code: int):
        super().__init__(response.get("error", {}).get("message", "API request failed"))
        self.response = response
        self.exit_code = exit_code


class APIClient:
    def __init__(self, base_url: str, timeout_seconds: float):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        command: str,
        *,
        path: str,
        method: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        query = parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        endpoint = f"{self.base_url}{path}"
        if query:
            endpoint = f"{endpoint}?{query}"

        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(endpoint, method=method, data=body, headers=headers)
        request_meta = {
            "method": method,
            "path": path,
            "endpoint": endpoint,
            "params": params or {},
        }
        if payload is not None:
            request_meta["payload"] = payload

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else None
                return (
                    {
                        "ok": True,
                        "command": command,
                        "request": request_meta,
                        "status_code": response.status,
                        "data": data,
                    },
                    0,
                )
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                detail = raw or None
            return (
                {
                    "ok": False,
                    "command": command,
                    "request": request_meta,
                    "status_code": exc.code,
                    "error": {
                        "type": "http_error",
                        "message": str(exc),
                        "detail": detail,
                    },
                },
                1,
            )
        except error.URLError as exc:
            return (
                {
                    "ok": False,
                    "command": command,
                    "request": request_meta,
                    "status_code": None,
                    "error": {
                        "type": "connection_error",
                        "message": str(exc.reason),
                    },
                },
                1,
            )

    def request_or_raise(
        self,
        command: str,
        *,
        path: str,
        method: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response, exit_code = self.request(
            command,
            path=path,
            method=method,
            params=params,
            payload=payload,
        )
        if exit_code != 0:
            raise APIClientError(response, exit_code)
        return response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Grounded local wrapper around ClawScout mail/draft endpoints."
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("CLAWSCOUT_API_BASE_URL", DEFAULT_BASE_URL),
        help=f"ClawScout API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("CLAWSCOUT_API_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))),
        help=f"HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Print only the response data on success. On failure, print a compact error object.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON with no indentation.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    recent = subparsers.add_parser("recent-drafts")
    recent.add_argument("--limit", type=int, default=10)
    recent.add_argument("--status", default="approved")
    recent.add_argument("--lead-id")

    detail = subparsers.add_parser("draft-detail")
    detail.add_argument("--draft-id", required=True)

    send_status = subparsers.add_parser("send-status")
    send_status.add_argument("--draft-id", required=True)

    send = subparsers.add_parser("send-draft")
    send.add_argument("--draft-id", required=True)

    return parser.parse_args()


def handle_recent_drafts(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "recent-drafts",
        path=COMMAND_SPECS["recent-drafts"].path_template,
        method="GET",
        params={
            "status": args.status,
            "lead_id": args.lead_id,
            "page": 1,
            "page_size": min(args.limit, 200),
        },
    )
    if exit_code != 0:
        return response, exit_code
    drafts = response["data"] or []
    response["data"] = {
        "items": drafts[: args.limit],
        "count": min(len(drafts), args.limit),
        "status_filter": args.status,
    }
    return response, 0


def handle_draft_detail(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    return client.request(
        "draft-detail",
        path=COMMAND_SPECS["draft-detail"].path_template.format(draft_id=args.draft_id),
        method="GET",
    )


def handle_send_status(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        draft = client.request_or_raise(
            "draft-detail",
            path=COMMAND_SPECS["draft-detail"].path_template.format(draft_id=args.draft_id),
            method="GET",
        )["data"]
        deliveries = client.request_or_raise(
            "send-status",
            path=COMMAND_SPECS["send-status"].path_template.format(draft_id=args.draft_id),
            method="GET",
        )["data"]
    except APIClientError as exc:
        return exc.response, exc.exit_code

    latest_delivery = deliveries[0] if deliveries else None
    return (
        {
            "ok": True,
            "command": "send-status",
            "request": {
                "method": "GET",
                "path": COMMAND_SPECS["send-status"].path_template.format(draft_id=args.draft_id),
                "draft_id": args.draft_id,
            },
            "status_code": 200,
            "data": {
                "draft": draft,
                "latest_delivery": latest_delivery,
                "deliveries": deliveries,
            },
        },
        0,
    )


def handle_send_draft(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "send-draft",
        path=COMMAND_SPECS["send-draft"].path_template.format(draft_id=args.draft_id),
        method="POST",
    )
    if exit_code != 0:
        return response, exit_code

    delivery = response["data"] or {}
    response["data"] = {
        "delivery": delivery,
        "summary": {
            "draft_id": delivery.get("draft_id"),
            "delivery_id": delivery.get("id"),
            "provider": delivery.get("provider"),
            "recipient_email": delivery.get("recipient_email"),
            "status": delivery.get("status"),
            "provider_message_id": delivery.get("provider_message_id"),
            "sent_at": delivery.get("sent_at"),
            "error": delivery.get("error"),
        },
    }
    return response, 0


def main() -> int:
    args = parse_args()
    client = APIClient(args.base_url, args.timeout)

    handlers = {
        "recent-drafts": handle_recent_drafts,
        "draft-detail": handle_draft_detail,
        "send-status": handle_send_status,
        "send-draft": handle_send_draft,
    }
    response, exit_code = handlers[args.command](client, args)
    if args.data_only:
        if response.get("ok"):
            rendered = response.get("data")
        else:
            rendered = {
                "ok": False,
                "command": response.get("command"),
                "status_code": response.get("status_code"),
                "error": response.get("error"),
            }
    else:
        rendered = response

    print(json.dumps(rendered, ensure_ascii=False, indent=None if args.compact else 2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
