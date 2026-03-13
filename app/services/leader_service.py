from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, OutreachDraft, OutreachLog
from app.models.task_tracking import PipelineRun, TaskRun
from app.services.dashboard_service import (
    get_city_breakdown,
    get_dashboard_stats,
    get_industry_breakdown,
    get_source_performance,
)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _since(hours: int = 24) -> datetime:
    return _now_utc() - timedelta(hours=hours)


def _count_drafts(db: Session, *statuses: DraftStatus) -> int:
    stmt = select(func.count(OutreachDraft.id))
    if statuses:
        stmt = stmt.where(OutreachDraft.status.in_(statuses))
    return db.execute(stmt).scalar() or 0


def _count_drafts_since(db: Session, since: datetime) -> int:
    stmt = select(func.count(OutreachDraft.id)).where(OutreachDraft.generated_at >= since)
    return db.execute(stmt).scalar() or 0


def _count_pipeline_runs(db: Session, *, status: str | None = None, since: datetime | None = None) -> int:
    stmt = select(func.count(PipelineRun.id))
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    if since:
        stmt = stmt.where(PipelineRun.created_at >= since)
    return db.execute(stmt).scalar() or 0


def _count_task_runs(db: Session, *, status: str | None = None, since: datetime | None = None) -> int:
    stmt = select(func.count(TaskRun.task_id))
    if status:
        stmt = stmt.where(TaskRun.status == status)
    if since:
        stmt = stmt.where(TaskRun.updated_at >= since)
    return db.execute(stmt).scalar() or 0


def _count_activity_logs(db: Session, *, since: datetime | None = None) -> int:
    stmt = select(func.count(OutreachLog.id))
    if since:
        stmt = stmt.where(OutreachLog.created_at >= since)
    return db.execute(stmt).scalar() or 0


def _lead_name_map(db: Session, lead_ids: set) -> dict:
    if not lead_ids:
        return {}
    stmt = select(Lead.id, Lead.business_name).where(Lead.id.in_(lead_ids))
    return {lead_id: business_name for lead_id, business_name in db.execute(stmt).all()}


def _serialize_lead(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "business_name": lead.business_name,
        "industry": lead.industry,
        "city": lead.city,
        "status": lead.status,
        "score": lead.score,
        "quality": lead.quality,
        "source_name": lead.source.name if lead.source else None,
        "updated_at": lead.updated_at,
    }


def _serialize_draft(draft: OutreachDraft) -> dict:
    return {
        "id": draft.id,
        "lead_id": draft.lead_id,
        "lead_name": draft.lead.business_name if draft.lead else None,
        "status": draft.status,
        "subject": draft.subject,
        "generated_at": draft.generated_at,
        "reviewed_at": draft.reviewed_at,
        "sent_at": draft.sent_at,
    }


def _serialize_pipeline(run: PipelineRun) -> dict:
    return {
        "id": run.id,
        "lead_id": run.lead_id,
        "lead_name": run.lead.business_name if run.lead else None,
        "status": run.status,
        "current_step": run.current_step,
        "root_task_id": run.root_task_id,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def _serialize_task(task: TaskRun) -> dict:
    return {
        "task_id": task.task_id,
        "task_name": task.task_name,
        "queue": task.queue,
        "lead_id": task.lead_id,
        "lead_name": task.lead.business_name if task.lead else None,
        "pipeline_run_id": task.pipeline_run_id,
        "status": task.status,
        "current_step": task.current_step,
        "correlation_id": task.correlation_id,
        "error": task.error,
        "updated_at": task.updated_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
    }


def get_system_overview(db: Session) -> dict:
    stats = get_dashboard_stats(db)
    recent_window = _since(24)
    top_industry = next(iter(get_industry_breakdown(db)), None)
    top_city = next(iter(get_city_breakdown(db)), None)
    top_source = next(iter(get_source_performance(db)), None)

    return {
        "total_leads": stats["total_leads"],
        "qualified": stats["qualified"],
        "avg_score": stats["avg_score"],
        "conversion_rate": stats["conversion_rate"],
        "pipeline_velocity": stats["pipeline_velocity"],
        "drafts_pending_review": _count_drafts(db, DraftStatus.PENDING_REVIEW),
        "drafts_approved": _count_drafts(db, DraftStatus.APPROVED),
        "drafts_recent_24h": _count_drafts_since(db, recent_window),
        "pipelines_running": _count_pipeline_runs(db, status="running"),
        "pipelines_failed": _count_pipeline_runs(db, status="failed"),
        "pipelines_recent_24h": _count_pipeline_runs(db, since=recent_window),
        "running_tasks": _count_task_runs(db, status="running"),
        "retrying_tasks": _count_task_runs(db, status="retrying"),
        "failed_tasks": _count_task_runs(db, status="failed"),
        "recent_activity_24h": _count_activity_logs(db, since=recent_window),
        "performance_highlights": {
            "top_industry": top_industry["industry"] if top_industry else None,
            "top_city": top_city["city"] if top_city else None,
            "top_source": top_source["source"] if top_source else None,
        },
        "snapshot_at": _now_utc(),
    }


def list_top_leads(
    db: Session,
    *,
    limit: int = 10,
    status: LeadStatus | None = None,
) -> list[dict]:
    stmt = select(Lead).options(joinedload(Lead.source))
    if status:
        stmt = stmt.where(Lead.status == status)
    stmt = stmt.order_by(Lead.score.desc().nulls_last(), Lead.updated_at.desc()).limit(limit)
    leads = db.execute(stmt).scalars().unique().all()
    return [_serialize_lead(lead) for lead in leads]


def list_recent_drafts(
    db: Session,
    *,
    limit: int = 10,
    status: DraftStatus | None = None,
) -> list[dict]:
    stmt = select(OutreachDraft).options(joinedload(OutreachDraft.lead))
    if status:
        stmt = stmt.where(OutreachDraft.status == status)
    stmt = stmt.order_by(OutreachDraft.generated_at.desc()).limit(limit)
    drafts = db.execute(stmt).scalars().unique().all()
    return [_serialize_draft(draft) for draft in drafts]


def list_recent_pipelines(
    db: Session,
    *,
    limit: int = 10,
    status: str | None = None,
) -> list[dict]:
    stmt = select(PipelineRun).options(joinedload(PipelineRun.lead))
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    stmt = stmt.order_by(PipelineRun.updated_at.desc()).limit(limit)
    runs = db.execute(stmt).scalars().unique().all()
    return [_serialize_pipeline(run) for run in runs]


def get_task_health(db: Session, *, limit: int = 10) -> dict:
    running_stmt = (
        select(TaskRun)
        .options(joinedload(TaskRun.lead))
        .where(TaskRun.status == "running")
        .order_by(TaskRun.updated_at.desc())
        .limit(limit)
    )
    retrying_stmt = (
        select(TaskRun)
        .options(joinedload(TaskRun.lead))
        .where(TaskRun.status == "retrying")
        .order_by(TaskRun.updated_at.desc())
        .limit(limit)
    )
    failed_stmt = (
        select(TaskRun)
        .options(joinedload(TaskRun.lead))
        .where(TaskRun.status == "failed")
        .order_by(TaskRun.updated_at.desc())
        .limit(limit)
    )
    running = db.execute(running_stmt).scalars().unique().all()
    retrying = db.execute(retrying_stmt).scalars().unique().all()
    failed = db.execute(failed_stmt).scalars().unique().all()
    return {
        "running_count": _count_task_runs(db, status="running"),
        "retrying_count": _count_task_runs(db, status="retrying"),
        "failed_count": _count_task_runs(db, status="failed"),
        "running": [_serialize_task(task) for task in running],
        "retrying": [_serialize_task(task) for task in retrying],
        "failed": [_serialize_task(task) for task in failed],
    }


def list_recent_activity_items(db: Session, *, limit: int = 10) -> list[dict]:
    stmt = select(OutreachLog).order_by(OutreachLog.created_at.desc()).limit(limit)
    logs = db.execute(stmt).scalars().unique().all()
    lead_names = _lead_name_map(db, {log.lead_id for log in logs})
    return [
        {
            "id": log.id,
            "lead_id": log.lead_id,
            "lead_name": lead_names.get(log.lead_id),
            "draft_id": log.draft_id,
            "action": log.action,
            "actor": log.actor,
            "detail": log.detail,
            "created_at": log.created_at,
        }
        for log in logs
    ]
