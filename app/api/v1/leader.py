from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models.lead import LeadStatus
from app.models.outreach import DraftStatus
from app.schemas.leader import (
    LeaderActivityItemResponse,
    LeaderDraftSummaryResponse,
    LeaderLeadSummaryResponse,
    LeaderOverviewResponse,
    LeaderPipelineSummaryResponse,
    LeaderReplyItemResponse,
    LeaderReplySummaryResponse,
    LeaderTaskHealthResponse,
)
from app.services.dashboard_svc.leader_service import (
    get_reply_summary,
    get_system_overview,
    get_task_health,
    list_leader_replies,
    list_recent_activity_items,
    list_recent_drafts,
    list_recent_pipelines,
    list_top_leads,
)

router = APIRouter(prefix="/leader", tags=["leader"])


@router.get("/overview", response_model=LeaderOverviewResponse)
def overview(db: Session = Depends(get_session)):
    """Return a compact operational snapshot for a future leader layer."""
    return get_system_overview(db)


@router.get("/top-leads", response_model=list[LeaderLeadSummaryResponse])
def top_leads(
    limit: int = Query(10, ge=1, le=100),
    status: LeadStatus | None = None,
    db: Session = Depends(get_session),
):
    """Return the highest-scoring leads, optionally filtered by status."""
    return list_top_leads(db, limit=limit, status=status)


@router.get("/recent-drafts", response_model=list[LeaderDraftSummaryResponse])
def recent_drafts(
    limit: int = Query(10, ge=1, le=100),
    status: DraftStatus | None = None,
    db: Session = Depends(get_session),
):
    """Return recent outreach drafts with lead context for operator workflows."""
    return list_recent_drafts(db, limit=limit, status=status)


@router.get("/recent-pipelines", response_model=list[LeaderPipelineSummaryResponse])
def recent_pipelines(
    limit: int = Query(10, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_session),
):
    """Return recent pipeline runs for future leader monitoring and drill-down."""
    return list_recent_pipelines(db, limit=limit, status=status)


@router.get("/task-health", response_model=LeaderTaskHealthResponse)
def task_health(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Return recent running and failed tasks plus headline counts."""
    return get_task_health(db, limit=limit)


@router.get("/activity", response_model=list[LeaderActivityItemResponse])
def recent_activity(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Return recent operational activity with lead context."""
    return list_recent_activity_items(db, limit=limit)


@router.get("/replies/summary", response_model=LeaderReplySummaryResponse)
def reply_summary(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_session),
):
    """Return a grounded operational summary of recent inbound replies."""
    return get_reply_summary(db, hours=hours)


@router.get("/replies", response_model=list[LeaderReplyItemResponse])
def list_replies(
    limit: int = Query(10, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
    labels: str | None = None,
    classification_status: str | None = None,
    important_only: bool = False,
    needs_reviewer: bool = False,
    db: Session = Depends(get_session),
):
    """Return recent inbound replies for reply-centric leader workflows."""
    label_values = tuple(label.strip() for label in (labels or "").split(",") if label.strip())
    return list_leader_replies(
        db,
        limit=limit,
        hours=hours,
        labels=label_values,
        classification_status=classification_status,
        important_only=important_only,
        needs_reviewer=needs_reviewer,
    )
