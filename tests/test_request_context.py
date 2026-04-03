import asyncio
from types import SimpleNamespace

from starlette.datastructures import Headers

from app.api.request_context import RequestContextMiddleware
from app.api.v1.outreach import generate_draft_async
from app.api.v1.scoring import run_full_pipeline
from app.schemas.lead import LeadCreate
from app.services.leads.lead_service import create_lead
from app.services.pipeline.task_tracking_service import get_pipeline_run, get_task_run


def test_request_context_middleware_sets_headers_and_state():
    captured_scope: dict[str, object] = {}
    messages: list[dict] = []

    async def app(scope, receive, send):
        captured_scope["state"] = dict(scope["state"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = RequestContextMiddleware(app)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "headers": [(b"x-correlation-id", b"corr-123")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(middleware(scope, receive, send))

    response_headers = Headers(raw=messages[0]["headers"])
    assert response_headers["X-Request-ID"]
    assert response_headers["X-Correlation-ID"] == "corr-123"
    assert captured_scope["state"]["request_id"]
    assert captured_scope["state"]["correlation_id"] == "corr-123"


def test_async_outreach_propagates_request_correlation_id(db, monkeypatch):
    lead = create_lead(
        db,
        LeadCreate(
            business_name="Correlation Draft",
            city="Cordoba",
            email="hello@example.com",
        ),
    )
    captured: dict[str, object] = {}

    def fake_delay(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(id="draft-task-001")

    monkeypatch.setattr("app.api.v1.outreach.task_generate_draft.delay", fake_delay)

    payload = generate_draft_async(
        lead.id,
        request=SimpleNamespace(state=SimpleNamespace(correlation_id="corr-draft-001")),
        db=db,
    )

    assert payload["task_id"] == "draft-task-001"
    assert captured["kwargs"] == {"correlation_id": "corr-draft-001"}

    task_run = get_task_run(db, "draft-task-001")
    assert task_run is not None
    assert task_run.correlation_id == "corr-draft-001"


def test_pipeline_run_uses_request_correlation_id(db, monkeypatch):
    lead = create_lead(
        db,
        LeadCreate(
            business_name="Correlation Pipeline",
            city="Mendoza",
        ),
    )
    captured: dict[str, object] = {}

    def fake_delay(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return SimpleNamespace(id="pipeline-task-001")

    monkeypatch.setattr("app.api.v1.scoring.task_full_pipeline.delay", fake_delay)

    payload = run_full_pipeline(
        lead.id,
        request=SimpleNamespace(state=SimpleNamespace(correlation_id="corr-pipeline-001")),
        db=db,
    )

    assert payload["task_id"] == "pipeline-task-001"
    assert captured["kwargs"]["correlation_id"] == "corr-pipeline-001"

    pipeline_run = get_pipeline_run(db, payload["pipeline_run_id"])
    assert pipeline_run is not None
    assert pipeline_run.correlation_id == "corr-pipeline-001"

    task_run = get_task_run(db, "pipeline-task-001")
    assert task_run is not None
    assert task_run.correlation_id == "corr-pipeline-001"
