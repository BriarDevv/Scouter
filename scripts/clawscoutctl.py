#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_MAX_ATTEMPTS = 12
TERMINAL_TASK_STATUSES = {"succeeded", "failed"}
TERMINAL_PIPELINE_STATUSES = {"succeeded", "failed"}


@dataclass(frozen=True)
class CommandSpec:
    method: str
    path_template: str
    mutating: bool = False
    timeout_seconds: float | None = None


COMMAND_SPECS: dict[str, CommandSpec] = {
    "overview": CommandSpec("GET", "/leader/overview"),
    "settings-mail": CommandSpec("GET", "/settings/mail"),
    "replies-summary": CommandSpec("GET", "/leader/replies/summary"),
    "recent-replies": CommandSpec("GET", "/leader/replies"),
    "top-leads": CommandSpec("GET", "/leader/top-leads"),
    "recent-drafts": CommandSpec("GET", "/leader/recent-drafts"),
    "recent-pipelines": CommandSpec("GET", "/leader/recent-pipelines"),
    "task-health": CommandSpec("GET", "/leader/task-health"),
    "activity": CommandSpec("GET", "/leader/activity"),
    "settings-llm": CommandSpec("GET", "/settings/llm"),
    "performance-industry": CommandSpec("GET", "/performance/industry"),
    "performance-city": CommandSpec("GET", "/performance/city"),
    "performance-source": CommandSpec("GET", "/performance/source"),
    "generate-draft": CommandSpec("POST", "/outreach/{lead_id}/draft/async", mutating=True),
    "run-pipeline": CommandSpec("POST", "/scoring/{lead_id}/pipeline", mutating=True),
    "task-status": CommandSpec("GET", "/tasks/{task_id}/status"),
    "review-lead": CommandSpec("POST", "/reviews/leads/{lead_id}/async", mutating=True),
    "review-draft": CommandSpec("POST", "/reviews/drafts/{draft_id}/async", mutating=True),
    "review-reply": CommandSpec("POST", "/reviews/inbound/messages/{message_id}/async", mutating=True),
    "review-reply-sync": CommandSpec("POST", "/reviews/inbound/messages/{message_id}", mutating=True, timeout_seconds=300),
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
        timeout_seconds: float | None = None,
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
            with request.urlopen(req, timeout=timeout_seconds or self.timeout_seconds) as response:
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

    def request_or_raise(
        self,
        command: str,
        *,
        path: str,
        method: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        response, exit_code = self.request(
            command,
            path=path,
            method=method,
            params=params,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
        if exit_code != 0:
            raise APIClientError(response, exit_code)
        return response


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

    subparsers.add_parser("overview", aliases=["ops-overview"])
    subparsers.add_parser("settings-llm", aliases=["ops-settings-llm"])
    subparsers.add_parser("settings-mail", aliases=["ops-settings-mail"])
    replies_summary = subparsers.add_parser("replies-summary", aliases=["ops-replies-summary"])
    replies_summary.add_argument("--hours", type=int, default=24)

    recent_replies = subparsers.add_parser("recent-replies")
    recent_replies.add_argument("--limit", type=int, default=10)
    recent_replies.add_argument("--hours", type=int, default=24)
    recent_replies.add_argument("--labels")
    recent_replies.add_argument("--classification-status")

    important_replies = subparsers.add_parser("important-replies", aliases=["ops-important-replies"])
    important_replies.add_argument("--limit", type=int, default=10)
    important_replies.add_argument("--hours", type=int, default=24)

    positive_replies = subparsers.add_parser("positive-replies")
    positive_replies.add_argument("--limit", type=int, default=10)
    positive_replies.add_argument("--hours", type=int, default=24)

    quote_replies = subparsers.add_parser("quote-replies")
    quote_replies.add_argument("--limit", type=int, default=10)
    quote_replies.add_argument("--hours", type=int, default=24)

    meeting_replies = subparsers.add_parser("meeting-replies")
    meeting_replies.add_argument("--limit", type=int, default=10)
    meeting_replies.add_argument("--hours", type=int, default=24)

    reviewer_candidates = subparsers.add_parser("reviewer-candidates")
    reviewer_candidates.add_argument("--limit", type=int, default=10)
    reviewer_candidates.add_argument("--hours", type=int, default=24)

    performance_summary = subparsers.add_parser("performance-summary")
    performance_summary.add_argument("--limit", type=int, default=3)

    top_leads = subparsers.add_parser("top-leads", aliases=["ops-top-leads"])
    top_leads.add_argument("--limit", type=int, default=10)
    top_leads.add_argument("--status")

    best_leads = subparsers.add_parser("best-leads")
    best_leads.add_argument("--limit", type=int, default=10)
    best_leads.add_argument("--status")

    recent_drafts = subparsers.add_parser("recent-drafts", aliases=["ops-recent-drafts"])
    recent_drafts.add_argument("--limit", type=int, default=10)
    recent_drafts.add_argument("--status")

    drafts_ready = subparsers.add_parser("drafts-ready")
    drafts_ready.add_argument("--limit", type=int, default=10)

    recent_pipelines = subparsers.add_parser("recent-pipelines")
    recent_pipelines.add_argument("--limit", type=int, default=10)
    recent_pipelines.add_argument("--status")

    task_health = subparsers.add_parser("task-health")
    task_health.add_argument("--limit", type=int, default=10)

    running_tasks = subparsers.add_parser("running-tasks")
    running_tasks.add_argument("--limit", type=int, default=10)

    failed_tasks = subparsers.add_parser("failed-tasks")
    failed_tasks.add_argument("--limit", type=int, default=10)

    activity = subparsers.add_parser("activity")
    activity.add_argument("--limit", type=int, default=10)

    generate_draft = subparsers.add_parser("generate-draft")
    generate_draft.add_argument("--lead-id", required=True)
    _add_wait_args(generate_draft)

    run_pipeline = subparsers.add_parser("run-pipeline")
    run_pipeline.add_argument("--lead-id", required=True)
    _add_wait_args(run_pipeline)

    task_status = subparsers.add_parser("task-status")
    task_status.add_argument("--task-id", required=True)

    wait_task = subparsers.add_parser("wait-task")
    wait_task.add_argument("--task-id", required=True)
    wait_task.add_argument("--interval", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS)
    wait_task.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)

    review_lead = subparsers.add_parser("review-lead")
    review_lead.add_argument("--lead-id", required=True)
    _add_wait_args(review_lead)

    review_draft = subparsers.add_parser("review-draft")
    review_draft.add_argument("--draft-id", required=True)
    _add_wait_args(review_draft)

    review_reply = subparsers.add_parser("review-reply")
    review_reply.add_argument("--message-id", required=True)
    review_reply.add_argument("--sync", action="store_true")
    _add_wait_args(review_reply)

    return parser.parse_args()


def _add_wait_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--interval", type=float, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)


def build_request(args: argparse.Namespace) -> tuple[str, str, dict[str, Any] | None]:
    command = args.command
    direct_command = {
        "best-leads": "top-leads",
        "drafts-ready": "recent-drafts",
        "ops-overview": "overview",
        "ops-settings-llm": "settings-llm",
        "ops-settings-mail": "settings-mail",
        "ops-replies-summary": "replies-summary",
        "ops-important-replies": "important-replies",
        "ops-top-leads": "top-leads",
        "ops-recent-drafts": "recent-drafts",
    }.get(command, command)
    spec = COMMAND_SPECS[direct_command]
    params: dict[str, Any] | None = None

    if direct_command == "replies-summary":
        params = {"hours": args.hours}
        path = spec.path_template
    elif direct_command == "recent-replies":
        params = {
            "limit": args.limit,
            "hours": args.hours,
            "labels": getattr(args, "labels", None),
            "classification_status": getattr(args, "classification_status", None),
        }
        path = spec.path_template
    elif direct_command == "top-leads":
        params = {"limit": args.limit, "status": getattr(args, "status", None)}
        path = spec.path_template
    elif direct_command == "recent-drafts":
        status = getattr(args, "status", None)
        if command == "drafts-ready":
            status = "pending_review"
        params = {"limit": args.limit, "status": status}
        path = spec.path_template
    elif direct_command == "recent-pipelines":
        params = {"limit": args.limit, "status": getattr(args, "status", None)}
        path = spec.path_template
    elif direct_command == "task-health":
        params = {"limit": args.limit}
        path = spec.path_template
    elif direct_command == "activity":
        params = {"limit": args.limit}
        path = spec.path_template
    elif direct_command == "generate-draft":
        path = spec.path_template.format(lead_id=args.lead_id)
    elif direct_command == "run-pipeline":
        path = spec.path_template.format(lead_id=args.lead_id)
    elif direct_command == "task-status":
        path = spec.path_template.format(task_id=args.task_id)
    elif direct_command == "review-lead":
        path = spec.path_template.format(lead_id=args.lead_id)
    elif direct_command == "review-draft":
        path = spec.path_template.format(draft_id=args.draft_id)
    elif direct_command == "review-reply":
        path = spec.path_template.format(message_id=args.message_id)
    else:
        path = spec.path_template

    return direct_command, spec.method, path, params


def make_success(
    command: str,
    *,
    data: Any,
    request_meta: dict[str, Any] | None = None,
    status_code: int = 200,
) -> tuple[dict[str, Any], int]:
    return (
        {
            "ok": True,
            "command": command,
            "request": request_meta or {},
            "status_code": status_code,
            "data": data,
        },
        0,
    )


def fetch_settings(client: APIClient) -> dict[str, Any]:
    return client.request_or_raise("settings-llm", path="/settings/llm", method="GET")["data"]


def _reply_list_response(
    response: dict[str, Any],
    *,
    command: str,
    filters: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    items = response["data"] or []
    return make_success(
        command,
        data={
            "count": len(items),
            "filters": filters,
            "items": items,
        },
        request_meta=response["request"],
        status_code=response["status_code"],
    )


def fetch_latest_draft_for_lead(client: APIClient, lead_id: str | None) -> dict[str, Any] | None:
    if not lead_id:
        return None
    response = client.request_or_raise(
        "list-drafts",
        path="/outreach/drafts",
        method="GET",
        params={"lead_id": lead_id, "page": 1, "page_size": 1},
    )
    drafts = response["data"] or []
    return drafts[0] if drafts else None


def fetch_draft_for_lead(client: APIClient, lead_id: str | None, draft_id: str | None) -> dict[str, Any] | None:
    if not lead_id:
        return None
    if not draft_id:
        return fetch_latest_draft_for_lead(client, lead_id)
    response = client.request_or_raise(
        "list-drafts",
        path="/outreach/drafts",
        method="GET",
        params={"lead_id": lead_id, "page": 1, "page_size": 20},
    )
    drafts = response["data"] or []
    for draft in drafts:
        if draft.get("id") == draft_id:
            return draft
    return None


def fetch_pipeline_run(client: APIClient, pipeline_run_id: str | None) -> dict[str, Any] | None:
    if not pipeline_run_id:
        return None
    response = client.request_or_raise(
        "pipeline-run",
        path=f"/pipelines/runs/{pipeline_run_id}",
        method="GET",
    )
    return response["data"]


def wait_for_pipeline_run(
    client: APIClient,
    *,
    pipeline_run_id: str,
    interval: float,
    max_attempts: int,
) -> dict[str, Any]:
    final: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        final = fetch_pipeline_run(client, pipeline_run_id)
        status = (final or {}).get("status")
        if status in TERMINAL_PIPELINE_STATUSES:
            return {
                "completed": True,
                "attempts": attempt,
                "interval_seconds": interval,
                "final": final,
            }
        if attempt < max_attempts:
            time.sleep(interval)

    return {
        "completed": False,
        "attempts": max_attempts,
        "interval_seconds": interval,
        "final": final,
    }


def wait_for_task(
    client: APIClient,
    *,
    task_id: str,
    interval: float,
    max_attempts: int,
) -> dict[str, Any]:
    final_response: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        final_response = client.request_or_raise(
            "task-status",
            path=f"/tasks/{task_id}/status",
            method="GET",
        )
        status = (final_response["data"] or {}).get("status")
        if status in TERMINAL_TASK_STATUSES:
            return {
                "completed": True,
                "attempts": attempt,
                "interval_seconds": interval,
                "final": final_response["data"],
            }
        if attempt < max_attempts:
            time.sleep(interval)

    return {
        "completed": False,
        "attempts": max_attempts,
        "interval_seconds": interval,
        "final": final_response["data"] if final_response else None,
    }


def summarize_wait_result(
    *,
    workflow: str,
    wait_data: dict[str, Any],
    configured_role: str,
    configured_model: str | None,
    latest_draft: dict[str, Any] | None = None,
    pipeline_run: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final = wait_data.get("final") or {}
    result = final.get("result") or {}
    return {
        "workflow": workflow,
        "configured_role": configured_role,
        "configured_model": configured_model,
        "task_status": final.get("status"),
        "lead_id": final.get("lead_id"),
        "pipeline_run_id": final.get("pipeline_run_id"),
        "current_step": final.get("current_step"),
        "draft_id": result.get("draft_id") or (latest_draft or {}).get("id"),
        "error": final.get("error"),
        "result": result,
        "latest_draft": latest_draft,
        "pipeline_run": pipeline_run,
    }


def summarize_pipeline_wait_result(
    *,
    wait_data: dict[str, Any],
    configured_role: str,
    configured_model: str | None,
    latest_draft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final = wait_data.get("final") or {}
    result = final.get("result") or {}
    return {
        "workflow": "run-pipeline",
        "configured_role": configured_role,
        "configured_model": configured_model,
        "pipeline_status": final.get("status"),
        "lead_id": final.get("lead_id"),
        "pipeline_run_id": final.get("id"),
        "current_step": final.get("current_step"),
        "draft_id": result.get("draft_id") or (latest_draft or {}).get("id"),
        "error": final.get("error"),
        "result": result,
        "latest_draft": latest_draft,
        "pipeline_run": final,
    }


def handle_direct_command(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    direct_command, method, path, params = build_request(args)
    return client.request(
        args.command,
        path=path,
        method=method,
        params=params,
        timeout_seconds=COMMAND_SPECS[direct_command].timeout_seconds,
    )


def handle_performance_summary(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        industry = client.request_or_raise(
            "performance-industry",
            path=COMMAND_SPECS["performance-industry"].path_template,
            method="GET",
        )["data"]
        city = client.request_or_raise(
            "performance-city",
            path=COMMAND_SPECS["performance-city"].path_template,
            method="GET",
        )["data"]
        source = client.request_or_raise(
            "performance-source",
            path=COMMAND_SPECS["performance-source"].path_template,
            method="GET",
        )["data"]
    except APIClientError as exc:
        return exc.response, exc.exit_code

    data = {
        "top_industry": industry[0] if industry else None,
        "top_city": city[0] if city else None,
        "top_source": source[0] if source else None,
        "industry": industry[: args.limit],
        "city": city[: args.limit],
        "source": source[: args.limit],
    }
    return make_success("performance-summary", data=data)


def handle_running_tasks(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "task-health",
        path=COMMAND_SPECS["task-health"].path_template,
        method="GET",
        params={"limit": args.limit},
    )
    if exit_code != 0:
        return response, exit_code
    health = response["data"]
    data = {
        "running_count": health["running_count"],
        "retrying_count": health["retrying_count"],
        "items": health["running"] + health["retrying"],
    }
    return make_success("running-tasks", data=data, request_meta=response["request"], status_code=response["status_code"])


def handle_failed_tasks(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "task-health",
        path=COMMAND_SPECS["task-health"].path_template,
        method="GET",
        params={"limit": args.limit},
    )
    if exit_code != 0:
        return response, exit_code
    health = response["data"]
    data = {
        "failed_count": health["failed_count"],
        "items": health["failed"],
    }
    return make_success("failed-tasks", data=data, request_meta=response["request"], status_code=response["status_code"])


def handle_replies_summary(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    return client.request(
        "replies-summary",
        path=COMMAND_SPECS["replies-summary"].path_template,
        method="GET",
        params={"hours": args.hours},
    )


def handle_recent_replies(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "recent-replies",
        path=COMMAND_SPECS["recent-replies"].path_template,
        method="GET",
        params={
            "limit": args.limit,
            "hours": args.hours,
            "labels": args.labels,
            "classification_status": args.classification_status,
        },
    )
    if exit_code != 0:
        return response, exit_code
    return _reply_list_response(
        response,
        command="recent-replies",
        filters={
            "limit": args.limit,
            "hours": args.hours,
            "labels": args.labels,
            "classification_status": args.classification_status,
        },
    )


def handle_important_replies(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "important-replies",
        path=COMMAND_SPECS["recent-replies"].path_template,
        method="GET",
        params={
            "limit": args.limit,
            "hours": args.hours,
            "important_only": True,
        },
    )
    if exit_code != 0:
        return response, exit_code
    return _reply_list_response(
        response,
        command="important-replies",
        filters={"limit": args.limit, "hours": args.hours, "important_only": True},
    )


def handle_positive_replies(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    labels = "interested,asked_for_quote,asked_for_meeting,asked_for_more_info"
    response, exit_code = client.request(
        "positive-replies",
        path=COMMAND_SPECS["recent-replies"].path_template,
        method="GET",
        params={
            "limit": args.limit,
            "hours": args.hours,
            "labels": labels,
        },
    )
    if exit_code != 0:
        return response, exit_code
    return _reply_list_response(
        response,
        command="positive-replies",
        filters={"limit": args.limit, "hours": args.hours, "labels": labels},
    )


def handle_quote_replies(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "quote-replies",
        path=COMMAND_SPECS["recent-replies"].path_template,
        method="GET",
        params={
            "limit": args.limit,
            "hours": args.hours,
            "labels": "asked_for_quote",
        },
    )
    if exit_code != 0:
        return response, exit_code
    return _reply_list_response(
        response,
        command="quote-replies",
        filters={"limit": args.limit, "hours": args.hours, "labels": "asked_for_quote"},
    )


def handle_meeting_replies(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "meeting-replies",
        path=COMMAND_SPECS["recent-replies"].path_template,
        method="GET",
        params={
            "limit": args.limit,
            "hours": args.hours,
            "labels": "asked_for_meeting",
        },
    )
    if exit_code != 0:
        return response, exit_code
    return _reply_list_response(
        response,
        command="meeting-replies",
        filters={"limit": args.limit, "hours": args.hours, "labels": "asked_for_meeting"},
    )


def handle_reviewer_candidates(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "reviewer-candidates",
        path=COMMAND_SPECS["recent-replies"].path_template,
        method="GET",
        params={
            "limit": args.limit,
            "hours": args.hours,
            "needs_reviewer": True,
        },
    )
    if exit_code != 0:
        return response, exit_code
    return _reply_list_response(
        response,
        command="reviewer-candidates",
        filters={"limit": args.limit, "hours": args.hours, "needs_reviewer": True},
    )


def handle_wait_task(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        data = wait_for_task(
            client,
            task_id=args.task_id,
            interval=args.interval,
            max_attempts=args.max_attempts,
        )
    except APIClientError as exc:
        return exc.response, exc.exit_code
    return make_success("wait-task", data=data)


def handle_generate_draft(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "generate-draft",
        path=COMMAND_SPECS["generate-draft"].path_template.format(lead_id=args.lead_id),
        method="POST",
    )
    if exit_code != 0 or not args.wait:
        return response, exit_code

    try:
        wait_data = wait_for_task(
            client,
            task_id=response["data"]["task_id"],
            interval=args.interval,
            max_attempts=args.max_attempts,
        )
        settings = fetch_settings(client)
        final_result = (wait_data.get("final") or {}).get("result") or {}
        latest_draft = None
        if wait_data.get("completed") and final_result.get("draft_id"):
            latest_draft = fetch_draft_for_lead(
                client,
                response["data"].get("lead_id"),
                final_result.get("draft_id"),
            )
    except APIClientError as exc:
        return exc.response, exc.exit_code

    data = {
        "enqueued": response["data"],
        "wait": wait_data,
        "summary": summarize_wait_result(
            workflow="generate-draft",
            wait_data=wait_data,
            configured_role="executor",
            configured_model=settings["executor_model"],
            latest_draft=latest_draft,
        ),
    }
    return make_success("generate-draft", data=data, request_meta=response["request"], status_code=response["status_code"])


def handle_run_pipeline(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "run-pipeline",
        path=COMMAND_SPECS["run-pipeline"].path_template.format(lead_id=args.lead_id),
        method="POST",
    )
    if exit_code != 0 or not args.wait:
        return response, exit_code

    try:
        settings = fetch_settings(client)
        pipeline_wait = wait_for_pipeline_run(
            client,
            pipeline_run_id=response["data"]["pipeline_run_id"],
            interval=args.interval,
            max_attempts=args.max_attempts,
        )
        final_pipeline = pipeline_wait.get("final") or {}
        latest_draft = None
        if pipeline_wait.get("completed") and (final_pipeline.get("result") or {}).get("draft_id"):
            latest_draft = fetch_draft_for_lead(
                client,
                response["data"].get("lead_id"),
                (final_pipeline.get("result") or {}).get("draft_id"),
            )
    except APIClientError as exc:
        return exc.response, exc.exit_code

    data = {
        "enqueued": response["data"],
        "wait": pipeline_wait,
        "summary": summarize_pipeline_wait_result(
            wait_data=pipeline_wait,
            configured_role="executor",
            configured_model=settings["executor_model"],
            latest_draft=latest_draft,
        ),
    }
    return make_success("run-pipeline", data=data, request_meta=response["request"], status_code=response["status_code"])


def handle_review_lead(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "review-lead",
        path=COMMAND_SPECS["review-lead"].path_template.format(lead_id=args.lead_id),
        method="POST",
    )
    if exit_code != 0 or not args.wait:
        return response, exit_code

    try:
        wait_data = wait_for_task(
            client,
            task_id=response["data"]["task_id"],
            interval=args.interval,
            max_attempts=args.max_attempts,
        )
        settings = fetch_settings(client)
    except APIClientError as exc:
        return exc.response, exc.exit_code

    data = {
        "enqueued": response["data"],
        "wait": wait_data,
        "summary": {
            "workflow": "review-lead",
            "configured_role": "reviewer",
            "configured_model": settings["reviewer_model"],
            "task_status": (wait_data.get("final") or {}).get("status"),
            "lead_id": (wait_data.get("final") or {}).get("lead_id"),
            "current_step": (wait_data.get("final") or {}).get("current_step"),
            "error": (wait_data.get("final") or {}).get("error"),
            "result": (wait_data.get("final") or {}).get("result"),
        },
    }
    return make_success("review-lead", data=data, request_meta=response["request"], status_code=response["status_code"])


def handle_review_draft(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    response, exit_code = client.request(
        "review-draft",
        path=COMMAND_SPECS["review-draft"].path_template.format(draft_id=args.draft_id),
        method="POST",
    )
    if exit_code != 0 or not args.wait:
        return response, exit_code

    try:
        wait_data = wait_for_task(
            client,
            task_id=response["data"]["task_id"],
            interval=args.interval,
            max_attempts=args.max_attempts,
        )
        settings = fetch_settings(client)
    except APIClientError as exc:
        return exc.response, exc.exit_code

    data = {
        "enqueued": response["data"],
        "wait": wait_data,
        "summary": {
            "workflow": "review-draft",
            "configured_role": "reviewer",
            "configured_model": settings["reviewer_model"],
            "task_status": (wait_data.get("final") or {}).get("status"),
            "lead_id": (wait_data.get("final") or {}).get("lead_id"),
            "current_step": (wait_data.get("final") or {}).get("current_step"),
            "error": (wait_data.get("final") or {}).get("error"),
            "result": (wait_data.get("final") or {}).get("result"),
        },
    }
    return make_success("review-draft", data=data, request_meta=response["request"], status_code=response["status_code"])


def handle_review_reply(client: APIClient, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        settings = fetch_settings(client)
    except APIClientError as exc:
        return exc.response, exc.exit_code

    if args.sync:
        response, exit_code = client.request(
            "review-reply",
            path=COMMAND_SPECS["review-reply-sync"].path_template.format(message_id=args.message_id),
            method="POST",
            timeout_seconds=COMMAND_SPECS["review-reply-sync"].timeout_seconds,
        )
        if exit_code != 0:
            return response, exit_code

        data = {
            "mode": "sync",
            "result": response["data"],
            "summary": {
                "workflow": "review-reply",
                "mode": "sync",
                "configured_role": "reviewer",
                "configured_model": settings["reviewer_model"],
                "inbound_message_id": response["data"].get("inbound_message_id"),
                "lead_id": response["data"].get("lead_id"),
                "classification_label": response["data"].get("classification_label"),
                "verdict": response["data"].get("verdict"),
                "confidence": response["data"].get("confidence"),
                "recommended_action": response["data"].get("recommended_action"),
            },
        }
        return make_success("review-reply", data=data, request_meta=response["request"], status_code=response["status_code"])

    response, exit_code = client.request(
        "review-reply",
        path=COMMAND_SPECS["review-reply"].path_template.format(message_id=args.message_id),
        method="POST",
    )
    if exit_code != 0 or not args.wait:
        if exit_code != 0:
            return response, exit_code
        data = {
            "mode": "async",
            "enqueued": response["data"],
            "summary": {
                "workflow": "review-reply",
                "mode": "async",
                "configured_role": "reviewer",
                "configured_model": settings["reviewer_model"],
                "task_id": response["data"].get("task_id"),
                "lead_id": response["data"].get("lead_id"),
                "current_step": response["data"].get("current_step"),
            },
        }
        return make_success("review-reply", data=data, request_meta=response["request"], status_code=response["status_code"])

    try:
        wait_data = wait_for_task(
            client,
            task_id=response["data"]["task_id"],
            interval=args.interval,
            max_attempts=args.max_attempts,
        )
    except APIClientError as exc:
        return exc.response, exc.exit_code

    final = wait_data.get("final") or {}
    result = final.get("result") or {}
    data = {
        "mode": "async",
        "enqueued": response["data"],
        "wait": wait_data,
        "summary": {
            "workflow": "review-reply",
            "mode": "async",
            "configured_role": "reviewer",
            "configured_model": settings["reviewer_model"],
            "task_status": final.get("status"),
            "task_id": final.get("task_id"),
            "lead_id": final.get("lead_id"),
            "current_step": final.get("current_step"),
            "error": final.get("error"),
            "inbound_message_id": result.get("inbound_message_id"),
            "classification_label": result.get("classification_label"),
            "verdict": result.get("verdict"),
            "confidence": result.get("confidence"),
            "recommended_action": result.get("recommended_action"),
            "result": result,
        },
    }
    return make_success("review-reply", data=data, request_meta=response["request"], status_code=response["status_code"])


def main() -> int:
    args = parse_args()
    client = APIClient(base_url=args.base_url, timeout_seconds=args.timeout)

    handlers = {
        "replies-summary": handle_replies_summary,
        "recent-replies": handle_recent_replies,
        "important-replies": handle_important_replies,
        "positive-replies": handle_positive_replies,
        "quote-replies": handle_quote_replies,
        "meeting-replies": handle_meeting_replies,
        "reviewer-candidates": handle_reviewer_candidates,
        "performance-summary": handle_performance_summary,
        "running-tasks": handle_running_tasks,
        "failed-tasks": handle_failed_tasks,
        "wait-task": handle_wait_task,
        "generate-draft": handle_generate_draft,
        "run-pipeline": handle_run_pipeline,
        "review-lead": handle_review_lead,
        "review-draft": handle_review_draft,
        "review-reply": handle_review_reply,
    }

    if args.command in handlers:
        response, exit_code = handlers[args.command](client, args)
    else:
        response, exit_code = handle_direct_command(client, args)

        if exit_code == 0 and args.command == "best-leads":
            response["data"] = {
                "count": len(response["data"]),
                "items": response["data"],
            }
        elif exit_code == 0 and args.command == "drafts-ready":
            response["data"] = {
                "count": len(response["data"]),
                "items": response["data"],
            }

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

    json.dump(rendered, sys.stdout, indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
