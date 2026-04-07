from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, literal, select
from sqlalchemy.orm import Session, joinedload

from app.models.inbound_mail import EmailThread, InboundMailClassificationStatus, InboundMessage
from app.models.lead import Lead, LeadStatus
from app.models.outreach import DraftStatus, OutreachDraft, OutreachLog
from app.models.task_tracking import PipelineRun, TaskRun
from app.services.dashboard.dashboard_service import (
    _load_leads as _dashboard_load_leads,
)
from app.services.dashboard.dashboard_service import (
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


def _count_pipeline_runs(
    db: Session, *, status: str | None = None, since: datetime | None = None
) -> int:
    stmt = select(func.count(PipelineRun.id))
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    if since:
        stmt = stmt.where(PipelineRun.created_at >= since)
    return db.execute(stmt).scalar() or 0


def _count_task_runs(
    db: Session, *, status: str | None = None, since: datetime | None = None
) -> int:
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


POSITIVE_REPLY_LABELS = {
    "interested",
    "asked_for_quote",
    "asked_for_meeting",
    "asked_for_more_info",
}

ACTIONABLE_REPLY_LABELS = POSITIVE_REPLY_LABELS | {
    "needs_human_review",
    "wrong_contact",
}


def _count_inbound_messages(
    db: Session,
    *,
    since: datetime | None = None,
    label: str | None = None,
    labels: set[str] | None = None,
    classification_status: str | None = None,
    needs_reviewer: bool | None = None,
    matched_via: str | None = None,
) -> int:
    stmt = select(func.count(InboundMessage.id))
    if since:
        stmt = stmt.where(InboundMessage.received_at >= since)
    if label:
        stmt = stmt.where(InboundMessage.classification_label == label)
    if labels:
        stmt = stmt.where(InboundMessage.classification_label.in_(sorted(labels)))
    if classification_status:
        stmt = stmt.where(InboundMessage.classification_status == classification_status)
    if needs_reviewer is not None:
        stmt = stmt.where(InboundMessage.should_escalate_reviewer.is_(needs_reviewer))
    if matched_via:
        stmt = stmt.where(InboundMessage.matched_via == matched_via)
    return db.execute(stmt).scalar() or 0


def _count_replied_leads(db: Session, *, since: datetime | None = None) -> int:
    stmt = select(func.count(func.distinct(InboundMessage.lead_id))).where(
        InboundMessage.lead_id.is_not(None)
    )
    if since:
        stmt = stmt.where(InboundMessage.received_at >= since)
    return db.execute(stmt).scalar() or 0


def _latest_reply_at(db: Session, *, since: datetime | None = None) -> datetime | None:
    stmt = select(func.max(InboundMessage.received_at))
    if since:
        stmt = stmt.where(InboundMessage.received_at >= since)
    return db.execute(stmt).scalar()


def _reply_priority_score(message: InboundMessage) -> int:
    base = {
        "asked_for_meeting": 115,
        "asked_for_quote": 110,
        "interested": 95,
        "asked_for_more_info": 90,
        "needs_human_review": 75,
        "wrong_contact": 60,
        "neutral": 40,
        "out_of_office": 20,
        "spam_or_irrelevant": 10,
        "not_interested": 5,
    }.get(message.classification_label or "", 30)

    if message.should_escalate_reviewer:
        base += 15
    if message.classification_status == InboundMailClassificationStatus.PENDING.value:
        base += 10
    elif message.classification_status == InboundMailClassificationStatus.FAILED.value:
        base += 5

    match_boost = int((((message.thread.match_confidence if message.thread else None) or 0) * 10))
    return base + match_boost


def _serialize_reply(message: InboundMessage) -> dict:
    return {
        "id": message.id,
        "thread_id": message.thread_id,
        "lead_id": message.lead_id,
        "lead_name": message.lead.business_name if message.lead else None,
        "draft_id": message.draft_id,
        "delivery_id": message.delivery_id,
        "from_email": message.from_email,
        "subject": message.subject,
        "body_snippet": message.body_snippet,
        "classification_status": message.classification_status,
        "classification_label": message.classification_label,
        "summary": message.summary,
        "confidence": message.confidence,
        "next_action_suggestion": message.next_action_suggestion,
        "should_escalate_reviewer": message.should_escalate_reviewer,
        "matched_via": message.thread.matched_via if message.thread else "unmatched",
        "match_confidence": message.thread.match_confidence if message.thread else 0.0,
        "received_at": message.received_at,
        "classification_role": message.classification_role,
        "classification_model": message.classification_model,
        "priority_score": _reply_priority_score(message),
    }


def get_system_overview(db: Session) -> dict:
    all_leads = _dashboard_load_leads(db)
    stats = get_dashboard_stats(db, leads=all_leads)
    recent_window = _since(24)
    top_industry = next(iter(get_industry_breakdown(db, leads=all_leads)), None)
    top_city = next(iter(get_city_breakdown(db, leads=all_leads)), None)
    top_source = next(iter(get_source_performance(db, leads=all_leads)), None)

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


def get_reply_summary(db: Session, *, hours: int = 24) -> dict:
    since = _since(hours)
    stmt = select(InboundMessage).where(InboundMessage.received_at >= since)
    messages = list(db.execute(stmt).scalars().all())

    important_replies = sum(
        1
        for message in messages
        if (
            message.should_escalate_reviewer
            or message.classification_status
            in {
                InboundMailClassificationStatus.PENDING.value,
                InboundMailClassificationStatus.FAILED.value,
            }
            or (message.classification_label in ACTIONABLE_REPLY_LABELS)
        )
    )

    return {
        "since_hours": hours,
        "since_at": since,
        "snapshot_at": _now_utc(),
        "latest_reply_at": _latest_reply_at(db, since=since),
        "total_recent_replies": len(messages),
        "replied_leads": len({message.lead_id for message in messages if message.lead_id}),
        "positive_replies": sum(
            1 for message in messages if message.classification_label in POSITIVE_REPLY_LABELS
        ),
        "interested_replies": sum(
            1 for message in messages if message.classification_label == "interested"
        ),
        "quote_replies": sum(
            1 for message in messages if message.classification_label == "asked_for_quote"
        ),
        "meeting_replies": sum(
            1 for message in messages if message.classification_label == "asked_for_meeting"
        ),
        "reviewer_candidates": sum(1 for message in messages if message.should_escalate_reviewer),
        "important_replies": important_replies,
        "pending_classification": sum(
            1
            for message in messages
            if message.classification_status == InboundMailClassificationStatus.PENDING.value
        ),
        "failed_classification": sum(
            1
            for message in messages
            if message.classification_status == InboundMailClassificationStatus.FAILED.value
        ),
        "unmatched_replies": sum(
            1
            for message in messages
            if (message.thread.matched_via if message.thread else "unmatched") == "unmatched"
        ),
    }


def _sql_priority_score():
    """Build a SQL expression mirroring ``_reply_priority_score``."""
    label_score = case(
        (InboundMessage.classification_label == "asked_for_meeting", 115),
        (InboundMessage.classification_label == "asked_for_quote", 110),
        (InboundMessage.classification_label == "interested", 95),
        (InboundMessage.classification_label == "asked_for_more_info", 90),
        (InboundMessage.classification_label == "needs_human_review", 75),
        (InboundMessage.classification_label == "wrong_contact", 60),
        (InboundMessage.classification_label == "neutral", 40),
        (InboundMessage.classification_label == "out_of_office", 20),
        (InboundMessage.classification_label == "spam_or_irrelevant", 10),
        (InboundMessage.classification_label == "not_interested", 5),
        else_=30,
    )
    escalate_boost = case(
        (InboundMessage.should_escalate_reviewer.is_(True), 15),
        else_=0,
    )
    status_boost = case(
        (InboundMessage.classification_status == InboundMailClassificationStatus.PENDING.value, 10),
        (InboundMessage.classification_status == InboundMailClassificationStatus.FAILED.value, 5),
        else_=0,
    )
    match_boost = func.cast(
        func.coalesce(EmailThread.match_confidence, literal(0)) * 10,
        literal(0).type,
    )
    return label_score + escalate_boost + status_boost + match_boost


def list_leader_replies(
    db: Session,
    *,
    limit: int = 10,
    hours: int = 24,
    labels: tuple[str, ...] = (),
    classification_status: str | None = None,
    important_only: bool = False,
    needs_reviewer: bool = False,
) -> list[dict]:
    since = _since(hours)
    stmt = (
        select(InboundMessage)
        .outerjoin(EmailThread, InboundMessage.thread_id == EmailThread.id)
        .options(joinedload(InboundMessage.lead), joinedload(InboundMessage.thread))
        .where(InboundMessage.received_at >= since)
    )
    if labels:
        stmt = stmt.where(InboundMessage.classification_label.in_(labels))
    if classification_status:
        stmt = stmt.where(InboundMessage.classification_status == classification_status)
    if needs_reviewer:
        stmt = stmt.where(InboundMessage.should_escalate_reviewer.is_(True))

    if important_only:
        stmt = stmt.where(
            (InboundMessage.should_escalate_reviewer.is_(True))
            | (
                InboundMessage.classification_status.in_(
                    [
                        InboundMailClassificationStatus.PENDING.value,
                        InboundMailClassificationStatus.FAILED.value,
                    ]
                )
            )
            | (InboundMessage.classification_label.in_(sorted(ACTIONABLE_REPLY_LABELS)))
        )
        stmt = stmt.order_by(
            _sql_priority_score().desc(),
            InboundMessage.received_at.desc().nulls_last(),
        )
    else:
        stmt = stmt.order_by(InboundMessage.received_at.desc().nulls_last())

    stmt = stmt.limit(limit)
    messages = list(db.execute(stmt).scalars().unique().all())
    return [_serialize_reply(message) for message in messages]
