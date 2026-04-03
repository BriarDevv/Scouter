"""AI Office API — agent status, decision log, and recommendations.

Provides the data layer for the /ai-office dashboard page.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models.conversation import Conversation, Message
from app.models.investigation_thread import InvestigationThread
from app.models.llm_invocation import LLMInvocation
from app.models.outcome_snapshot import OutcomeSnapshot
from app.models.review_correction import ReviewCorrection
from app.models.task_tracking import TaskRun

router = APIRouter(prefix="/ai-office", tags=["ai-office"])


@router.get("/status")
def get_agent_status(db: Session = Depends(get_session)):
    """Return status overview for all agents in the AI team."""
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)

    # Mote status
    latest_conversation = (
        db.query(Conversation)
        .order_by(Conversation.updated_at.desc())
        .first()
    )
    mote_last_active = latest_conversation.updated_at if latest_conversation else None
    active_conversations = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.is_active.is_(True))
        .scalar()
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

    # Approval rate (reviewer invocations that succeeded vs total)
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
    total_won = db.query(func.count(OutcomeSnapshot.id)).filter(OutcomeSnapshot.outcome == "won").scalar() or 0
    total_lost = db.query(func.count(OutcomeSnapshot.id)).filter(OutcomeSnapshot.outcome == "lost").scalar() or 0

    return {
        "agents": {
            "mote": {
                "name": "Mote",
                "role": "Jefe de operaciones",
                "model": "hermes3:8b",
                "status": "online" if mote_last_active and (now - mote_last_active).total_seconds() < 3600 else "idle",
                "last_active": mote_last_active.isoformat() if mote_last_active else None,
                "active_conversations": active_conversations,
            },
            "scout": {
                "name": "Scout",
                "role": "Investigador de campo",
                "model": "qwen3.5:9b",
                "status": "active" if active_research_tasks > 0 else "idle",
                "active_investigations": active_research_tasks,
                "investigations_24h": scout_investigations_24h,
            },
            "executor": {
                "name": "Executor",
                "role": "Analista",
                "model": "qwen3.5:9b",
                "status": "active" if executor_invocations_24h > 0 else "idle",
                "invocations_24h": executor_invocations_24h,
                "fallback_rate": round(executor_fallback_count / max(executor_invocations_24h, 1), 2),
            },
            "reviewer": {
                "name": "Reviewer",
                "role": "Control de calidad",
                "model": "qwen3.5:27b",
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


@router.get("/decisions")
def get_recent_decisions(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Return recent AI decisions across all agents."""
    invocations = (
        db.query(LLMInvocation)
        .order_by(LLMInvocation.created_at.desc())
        .limit(limit)
        .all()
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


@router.get("/investigations")
def get_recent_investigations(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_session),
):
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
