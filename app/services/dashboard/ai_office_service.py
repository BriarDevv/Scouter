"""Business logic for the AI Office dashboard endpoints."""

import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.investigation_thread import InvestigationThread
from app.models.llm_invocation import LLMInvocation
from app.models.outbound_conversation import OutboundConversation
from app.models.outcome_snapshot import OutcomeSnapshot
from app.models.review_correction import ReviewCorrection
from app.models.task_tracking import TaskRun


def get_agent_status(db: Session) -> dict:
    """Return status overview for all agents in the AI team."""
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)

    # Mote status
    latest_conversation = db.query(Conversation).order_by(Conversation.updated_at.desc()).first()
    mote_last_active = latest_conversation.updated_at if latest_conversation else None
    active_conversations = (
        db.query(func.count(Conversation.id)).filter(Conversation.is_active.is_(True)).scalar()
    ) or 0

    # Scout status (investigation threads in last 24h)
    scout_investigations_24h = (
        db.query(func.count(InvestigationThread.id))
        .filter(InvestigationThread.created_at >= last_24h)
        .scalar()
    ) or 0
    active_research_tasks = (
        db.query(func.count(TaskRun.task_id))
        .filter(
            TaskRun.task_name == "task_research_lead",
            TaskRun.status.in_(["running", "queued"]),
        )
        .scalar()
    ) or 0

    # Executor status (LLM invocations in last 24h)
    executor_invocations_24h = (
        db.query(func.count(LLMInvocation.id))
        .filter(
            LLMInvocation.created_at >= last_24h,
            LLMInvocation.role == "executor",
        )
        .scalar()
    ) or 0
    executor_fallback_count = (
        db.query(func.count(LLMInvocation.id))
        .filter(
            LLMInvocation.created_at >= last_24h,
            LLMInvocation.role == "executor",
            LLMInvocation.fallback_used.is_(True),
        )
        .scalar()
    ) or 0

    # Reviewer status
    reviewer_invocations_24h = (
        db.query(func.count(LLMInvocation.id))
        .filter(
            LLMInvocation.created_at >= last_24h,
            LLMInvocation.role == "reviewer",
        )
        .scalar()
    ) or 0
    corrections_7d = (
        db.query(func.count(ReviewCorrection.id))
        .filter(ReviewCorrection.created_at >= now - timedelta(days=7))
        .scalar()
    ) or 0

    reviewer_total = max(reviewer_invocations_24h, 1)
    reviewer_succeeded = (
        db.query(func.count(LLMInvocation.id))
        .filter(
            LLMInvocation.created_at >= last_24h,
            LLMInvocation.role == "reviewer",
            LLMInvocation.status == "succeeded",
        )
        .scalar()
    ) or 0

    # Outcomes
    total_won = (
        db.query(func.count(OutcomeSnapshot.id)).filter(OutcomeSnapshot.outcome == "won").scalar()
        or 0
    )
    total_lost = (
        db.query(func.count(OutcomeSnapshot.id)).filter(OutcomeSnapshot.outcome == "lost").scalar()
        or 0
    )

    return {
        "agents": {
            "mote": {
                "name": "Mote",
                "role": "Jefe de operaciones",
                "model": settings.ollama_agent_model,
                "status": (
                    "online"
                    if mote_last_active and (now - mote_last_active).total_seconds() < 3600
                    else "idle"
                ),
                "last_active": mote_last_active.isoformat() if mote_last_active else None,
                "active_conversations": active_conversations,
            },
            "scout": {
                "name": "Scout",
                "role": "Investigador de campo",
                "model": settings.ollama_executor_model,
                "status": "active" if active_research_tasks > 0 else "idle",
                "active_investigations": active_research_tasks,
                "investigations_24h": scout_investigations_24h,
            },
            "executor": {
                "name": "Executor",
                "role": "Analista",
                "model": settings.ollama_executor_model,
                "status": "active" if executor_invocations_24h > 0 else "idle",
                "invocations_24h": executor_invocations_24h,
                "fallback_rate": round(
                    executor_fallback_count / max(executor_invocations_24h, 1), 2
                ),
            },
            "reviewer": {
                "name": "Reviewer",
                "role": "Control de calidad",
                "model": settings.ollama_reviewer_model,
                "status": "active" if reviewer_invocations_24h > 0 else "idle",
                "invocations_24h": reviewer_invocations_24h,
                "approval_rate": round(reviewer_succeeded / reviewer_total, 2),
                "corrections_7d": corrections_7d,
            },
        },
        "outcomes": {
            "total_won": total_won,
            "total_lost": total_lost,
        },
    }


def get_recent_decisions(db: Session, limit: int) -> list[dict]:
    """Return recent AI decisions across all agents."""
    invocations = (
        db.query(LLMInvocation).order_by(LLMInvocation.created_at.desc()).limit(limit).all()
    )
    return [
        {
            "id": str(inv.id),
            "function_name": inv.function_name,
            "role": inv.role,
            "model": inv.model,
            "status": inv.status,
            "latency_ms": inv.latency_ms,
            "fallback_used": inv.fallback_used,
            "target_type": inv.target_type,
            "target_id": inv.target_id,
            "prompt_id": inv.prompt_id,
            "prompt_version": inv.prompt_version,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invocations
    ]


def get_recent_investigations(db: Session, limit: int) -> list[dict]:
    """Return recent Scout investigations."""
    threads = (
        db.query(InvestigationThread)
        .order_by(InvestigationThread.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(t.id),
            "lead_id": str(t.lead_id),
            "agent_model": t.agent_model,
            "pages_visited": t.pages_visited_json,
            "findings": t.findings_json,
            "loops_used": t.loops_used,
            "duration_ms": t.duration_ms,
            "error": t.error,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in threads
    ]


def get_outbound_conversations(db: Session, limit: int) -> list[dict]:
    """Return recent Mote outbound conversations."""
    convos = (
        db.query(OutboundConversation)
        .order_by(OutboundConversation.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(c.id),
            "lead_id": str(c.lead_id),
            "channel": c.channel,
            "status": c.status.value if hasattr(c.status, "value") else c.status,
            "mode": c.mode,
            "messages_count": len(c.messages_json or []),
            "operator_took_over": c.operator_took_over,
            "error": c.error,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convos
    ]


def get_conversation_detail(db: Session, conversation_id: uuid.UUID) -> dict | None:
    """Return full conversation thread with messages, or None if not found."""
    convo = db.get(OutboundConversation, conversation_id)
    if not convo:
        return None
    return {
        "id": str(convo.id),
        "lead_id": str(convo.lead_id),
        "draft_id": str(convo.draft_id) if convo.draft_id else None,
        "channel": convo.channel,
        "status": convo.status.value if hasattr(convo.status, "value") else convo.status,
        "mode": convo.mode,
        "messages": convo.messages_json or [],
        "operator_took_over": convo.operator_took_over,
        "provider_message_id": convo.provider_message_id,
        "error": convo.error,
        "created_at": convo.created_at.isoformat() if convo.created_at else None,
    }


def send_closer_reply(db: Session, conversation_id: uuid.UUID) -> dict:
    """Send Mote's latest response to the client via WhatsApp.

    Returns a dict with keys: status, message_preview (on success) or error (on failure).
    Raises ValueError with a user-facing message on validation failure.
    """
    convo = db.get(OutboundConversation, conversation_id)
    if not convo:
        raise ValueError("Conversation not found")

    if convo.operator_took_over:
        raise ValueError("Operator took over — Mote cannot send")

    messages = convo.messages_json or []
    mote_messages = [m for m in messages if m.get("role") == "mote"]
    if not mote_messages:
        raise ValueError("No Mote response to send")

    latest_response = mote_messages[-1]["content"]

    from app.models.lead import Lead

    lead = db.get(Lead, convo.lead_id)
    if not lead or not lead.phone:
        raise ValueError("Lead has no phone number")

    try:
        from app.services.comms.whatsapp_service import send_message_to_phone

        ok = send_message_to_phone(db, lead.phone, latest_response)
        if ok:
            return {"status": "sent", "message_preview": latest_response[:100]}
        return {"status": "failed", "error": "Provider returned false"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def test_send_whatsapp(phone: str, message: str) -> dict:
    """Validate phone format and send a test WhatsApp message.

    Returns a dict with keys: status, phone (masked), and message_id or error.
    Raises ValueError on invalid phone format.
    """
    clean_phone = re.sub(r"[^\d+]", "", phone)
    if len(clean_phone) < 8 or len(clean_phone) > 16:
        raise ValueError("Phone number must be 8-16 digits")

    try:
        from app.services.comms.kapso_service import send_text_message

        result = send_text_message(clean_phone, message)
        return {
            "status": "sent",
            "phone": clean_phone[:6] + "***",
            "message_id": result.get("message_id"),
            "message_preview": message[:100],
        }
    except Exception as exc:
        return {
            "status": "failed",
            "phone": clean_phone[:6] + "***",
            "error": str(exc),
        }


def get_weekly_reports(db: Session, limit: int) -> list[dict]:
    """Return recent weekly AI team reports."""
    from app.models.weekly_report import WeeklyReport

    reports = db.query(WeeklyReport).order_by(WeeklyReport.created_at.desc()).limit(limit).all()
    return [
        {
            "id": str(r.id),
            "week_start": r.week_start.isoformat(),
            "week_end": r.week_end.isoformat(),
            "metrics": r.metrics_json,
            "recommendations": r.recommendations_json,
            "synthesis": r.synthesis_text,
            "synthesis_model": r.synthesis_model,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]
