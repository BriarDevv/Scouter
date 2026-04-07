"""AI Office API — agent status, decision log, conversations, and recommendations.

Provides the data layer for the /ai-office dashboard page.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai_office import CloserReplyBody, TestWhatsAppBody
from app.services.dashboard import ai_office_service

router = APIRouter(prefix="/ai-office", tags=["ai-office"])


@router.get("/status")
def get_agent_status(db: Session = Depends(get_db)):  # noqa: B008
    """Return status overview for all agents in the AI team."""
    return ai_office_service.get_agent_status(db)


@router.get("/decisions")
def get_recent_decisions(
    limit: int = Query(default=20, ge=1, le=100),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return recent AI decisions across all agents."""
    return ai_office_service.get_recent_decisions(db, limit)


@router.get("/investigations")
def get_recent_investigations(
    limit: int = Query(default=10, ge=1, le=50),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return recent Scout investigations."""
    return ai_office_service.get_recent_investigations(db, limit)


@router.get("/conversations")
def get_outbound_conversations(
    limit: int = Query(default=20, ge=1, le=100),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return recent Mote outbound conversations."""
    return ai_office_service.get_outbound_conversations(db, limit)


@router.get("/conversations/{conversation_id}")
def get_conversation_detail(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return full conversation thread with messages."""
    detail = ai_office_service.get_conversation_detail(db, conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.post("/conversations/{conversation_id}/takeover")
def takeover_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Operator takes over a Mote conversation."""
    from app.services.outreach.auto_send_service import operator_takeover

    convo = operator_takeover(db, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.commit()
    return {
        "id": str(convo.id),
        "status": convo.status.value if hasattr(convo.status, "value") else convo.status,
        "operator_took_over": True,
    }


@router.post("/test-send-whatsapp")
def test_send_whatsapp(
    body: TestWhatsAppBody,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Test WhatsApp sending — sends a test message to the given phone number.

    Restricted: max 500 chars, basic phone validation, rate-limited by global limiter.
    """
    try:
        return ai_office_service.test_send_whatsapp(body.phone, body.message)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/conversations/{conversation_id}/reply")
def closer_reply(
    conversation_id: uuid.UUID,
    body: CloserReplyBody,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Mote generates a response to a client message (closer mode).

    Detects intent, uses full lead context (dossier, brief, research),
    and generates a personalized WhatsApp-style response.
    """
    from app.services.outreach.closer_service import generate_closer_response

    result = generate_closer_response(db, conversation_id, body.client_message)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/conversations/{conversation_id}/send-reply")
def send_closer_reply(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Send Mote's latest response to the client via WhatsApp.

    Takes the last mote message from the conversation and sends it.
    """
    try:
        return ai_office_service.send_closer_reply(db, conversation_id)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/weekly-reports")
def get_weekly_reports(
    limit: int = Query(default=5, ge=1, le=20),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Return recent weekly AI team reports."""
    return ai_office_service.get_weekly_reports(db, limit)


@router.post("/weekly-reports/generate")
def trigger_weekly_report(db: Session = Depends(get_db)):  # noqa: B008
    """Manually trigger a weekly report generation."""
    from app.workers.weekly_tasks import task_weekly_report

    task = task_weekly_report.delay()
    return {"status": "queued", "task_id": task.id}
