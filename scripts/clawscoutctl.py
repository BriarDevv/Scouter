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
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class CommandSpec:
    method: str
    path_template: str
    mutating: bool = False


COMMAND_SPECS: dict[str, CommandSpec] = {
    "overview": CommandSpec("GET", "/leader/overview"),
    "top-leads": CommandSpec("GET", "/leader/top-leads"),
    "recent-drafts": CommandSpec("GET", "/leader/recent-drafts"),
    "recent-pipelines": CommandSpec("GET", "/leader/recent-pipelines"),
    "task-health": CommandSpec("GET", "/leader/task-health"),
    "activity": CommandSpec("GET", "/leader/activity"),
    "settings-llm": CommandSpec("GET", "/settings/llm"),
    "generate-draft": CommandSpec("POST", "/outreach/{lead_id}/draft/async", mutating=True),
    "run-pipeline": CommandSpec("POST", "/scoring/{lead_id}/pipeline", mutating=True),
    "task-status": CommandSpec("GET", "/tasks/{task_id}/status"),
}


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
            detail: Any
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Thin local wrapper around the ClawScout HTTP API for OpenClaw leader workflows."
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("overview")
    subparsers.add_parser("settings-llm")

    top_leads = subparsers.add_parser("top-leads")
    top_leads.add_argument("--limit", type=int, default=10)
    top_leads.add_argument("--status")

    recent_drafts = subparsers.add_parser("recent-drafts")
    recent_drafts.add_argument("--limit", type=int, default=10)
    recent_drafts.add_argument("--status")

    recent_pipelines = subparsers.add_parser("recent-pipelines")
    recent_pipelines.add_argument("--limit", type=int, default=10)
    recent_pipelines.add_argument("--status")

    task_health = subparsers.add_parser("task-health")
    task_health.add_argument("--limit", type=int, default=10)

    activity = subparsers.add_parser("activity")
    activity.add_argument("--limit", type=int, default=10)

    generate_draft = subparsers.add_parser("generate-draft")
    generate_draft.add_argument("--lead-id", required=True)

    run_pipeline = subparsers.add_parser("run-pipeline")
    run_pipeline.add_argument("--lead-id", required=True)

    task_status = subparsers.add_parser("task-status")
    task_status.add_argument("--task-id", required=True)

    return parser.parse_args()


def build_request(args: argparse.Namespace) -> tuple[str, str, dict[str, Any] | None]:
    command = args.command
    spec = COMMAND_SPECS[command]
    params: dict[str, Any] | None = None

    if command == "top-leads":
        params = {"limit": args.limit, "status": args.status}
        path = spec.path_template
    elif command == "recent-drafts":
        params = {"limit": args.limit, "status": args.status}
        path = spec.path_template
    elif command == "recent-pipelines":
        params = {"limit": args.limit, "status": args.status}
        path = spec.path_template
    elif command == "task-health":
        params = {"limit": args.limit}
        path = spec.path_template
    elif command == "activity":
        params = {"limit": args.limit}
        path = spec.path_template
    elif command == "generate-draft":
        path = spec.path_template.format(lead_id=args.lead_id)
    elif command == "run-pipeline":
        path = spec.path_template.format(lead_id=args.lead_id)
    elif command == "task-status":
        path = spec.path_template.format(task_id=args.task_id)
    else:
        path = spec.path_template

    return spec.method, path, params


def main() -> int:
    args = parse_args()
    method, path, params = build_request(args)
    client = APIClient(base_url=args.base_url, timeout_seconds=args.timeout)
    response, exit_code = client.request(
        args.command,
        path=path,
        method=method,
        params=params,
    )
    json.dump(response, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
