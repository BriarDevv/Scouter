import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, select
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadStatus
from app.models.lead_source import LeadSource
from app.models.outreach import LogAction, OutreachDraft, OutreachLog

PIPELINE_STAGE_META = (
    (LeadStatus.NEW, "Nuevos", "#94a3b8"),
    (LeadStatus.ENRICHED, "Enriquecidos", "#60a5fa"),
    (LeadStatus.SCORED, "Puntuados", "#818cf8"),
    (LeadStatus.QUALIFIED, "Calificados", "#a78bfa"),
    (LeadStatus.DRAFT_READY, "Draft Listo", "#c084fc"),
    (LeadStatus.APPROVED, "Aprobados", "#22d3ee"),
    (LeadStatus.CONTACTED, "Contactados", "#fbbf24"),
    (LeadStatus.OPENED, "Abiertos", "#fb923c"),
    (LeadStatus.REPLIED, "Respondieron", "#34d399"),
    (LeadStatus.MEETING, "Reunión", "#2dd4bf"),
    (LeadStatus.WON, "Ganados", "#22c55e"),
)

PIPELINE_STAGE_ORDER = {status: index for index, (status, _, _) in enumerate(PIPELINE_STAGE_META)}
STATUS_PROGRESS_FALLBACK = {
    LeadStatus.LOST: PIPELINE_STAGE_ORDER[LeadStatus.CONTACTED],
    LeadStatus.SUPPRESSED: None,
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _date_key(value: datetime | None) -> str | None:
    normalized = _normalize_timestamp(value)
    return normalized.date().isoformat() if normalized else None


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _safe_average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stage_rank(status: LeadStatus) -> int | None:
    if status in PIPELINE_STAGE_ORDER:
        return PIPELINE_STAGE_ORDER[status]
    return STATUS_PROGRESS_FALLBACK.get(status)


def _reached_stage(status: LeadStatus, stage: LeadStatus) -> bool:
    current_rank = _stage_rank(status)
    target_rank = PIPELINE_STAGE_ORDER[stage]
    return current_rank is not None and current_rank >= target_rank


def _load_logs(db: Session, since: datetime | None = None) -> list[OutreachLog]:
    stmt = select(OutreachLog)
    if since:
        stmt = stmt.where(OutreachLog.created_at >= since)
    stmt = stmt.order_by(OutreachLog.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def _load_sent_drafts(db: Session, since: datetime | None = None) -> list[OutreachDraft]:
    stmt = select(OutreachDraft).where(OutreachDraft.sent_at.is_not(None))
    if since:
        stmt = stmt.where(OutreachDraft.sent_at >= since)
    return list(db.execute(stmt.order_by(OutreachDraft.sent_at.desc())).scalars().all())


def _last_lead_at(db: Session) -> str | None:
    """Retorna el max(created_at) de leads como ISO string o None."""
    result = db.execute(select(sa_func.max(Lead.created_at))).scalar()
    if result is None:
        return None
    normalized = _normalize_timestamp(result)
    return normalized.isoformat() if normalized else None


def _status_at_or_beyond(stage: LeadStatus):
    """Return a SQL CASE expression: 1 if lead has reached this stage, else 0."""
    target_rank = PIPELINE_STAGE_ORDER[stage]
    matching = [s for s, rank in PIPELINE_STAGE_ORDER.items() if rank >= target_rank]
    # Also include LOST (counts as having reached CONTACTED)
    if target_rank <= PIPELINE_STAGE_ORDER.get(LeadStatus.CONTACTED, 99):
        matching.append(LeadStatus.LOST)
    return sa_func.sum(case((Lead.status.in_(matching), 1), else_=0))


def get_dashboard_stats(db: Session, *, leads: list[Lead] | None = None) -> dict:
    # Legacy path: if pre-loaded leads are passed, use Python (for leader_service)
    if leads is not None:
        return _get_dashboard_stats_python(db, leads)

    today = _now_utc().date()
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

    row = db.execute(
        select(
            sa_func.count(Lead.id).label("total"),
            sa_func.count(case((Lead.created_at >= today_start, 1))).label("new_today"),
            sa_func.avg(Lead.score).label("avg_score"),
            _status_at_or_beyond(LeadStatus.QUALIFIED).label("qualified"),
            _status_at_or_beyond(LeadStatus.APPROVED).label("approved"),
            _status_at_or_beyond(LeadStatus.CONTACTED).label("contacted"),
            _status_at_or_beyond(LeadStatus.OPENED).label("opened"),
            _status_at_or_beyond(LeadStatus.REPLIED).label("replied"),
            _status_at_or_beyond(LeadStatus.MEETING).label("meetings"),
            sa_func.sum(case((Lead.status == LeadStatus.WON, 1), else_=0)).label("won"),
            sa_func.sum(case((Lead.status == LeadStatus.LOST, 1), else_=0)).label("lost"),
            sa_func.sum(case((Lead.status == LeadStatus.SUPPRESSED, 1), else_=0)).label(
                "suppressed"
            ),
        )
    ).one()

    total = row.total or 0
    contacted = row.contacted or 0
    opened = row.opened or 0
    replied = row.replied or 0
    meetings = row.meetings or 0
    won = row.won or 0

    # Pipeline velocity: avg days from created_at to updated_at for won/lost leads
    velocity_row = db.execute(
        select(
            sa_func.avg(sa_func.extract("epoch", Lead.updated_at - Lead.created_at) / 86400)
        ).where(Lead.status.in_([LeadStatus.WON, LeadStatus.LOST]))
    ).scalar()

    return {
        "total_leads": total,
        "new_today": row.new_today or 0,
        "qualified": row.qualified or 0,
        "approved": row.approved or 0,
        "contacted": contacted,
        "replied": replied,
        "meetings": meetings,
        "won": won,
        "lost": row.lost or 0,
        "suppressed": row.suppressed or 0,
        "avg_score": round(float(row.avg_score or 0), 1),
        "conversion_rate": round(_safe_rate(won, contacted), 4),
        "open_rate": round(_safe_rate(opened, contacted), 4),
        "reply_rate": round(_safe_rate(replied, contacted), 4),
        "positive_reply_rate": round(_safe_rate(meetings, replied), 4),
        "meeting_rate": round(_safe_rate(meetings, contacted), 4),
        "pipeline_velocity": round(float(velocity_row or 0), 1),
        "last_lead_at": _last_lead_at(db),
    }


def _get_dashboard_stats_python(db: Session, leads: list[Lead]) -> dict:
    """Fallback: compute stats from pre-loaded leads (used by leader_service)."""
    today = _now_utc().date()
    total_leads = len(leads)
    scored_values = [lead.score for lead in leads if lead.score is not None]
    new_today = sum(1 for lead in leads if _date_key(lead.created_at) == today.isoformat())
    qualified = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.QUALIFIED))
    approved = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.APPROVED))
    contacted = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.CONTACTED))
    opened = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.OPENED))
    replied = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.REPLIED))
    meetings = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.MEETING))
    won = sum(1 for lead in leads if lead.status == LeadStatus.WON)
    lost = sum(1 for lead in leads if lead.status == LeadStatus.LOST)
    suppressed = sum(1 for lead in leads if lead.status == LeadStatus.SUPPRESSED)

    closed_cycle_days = []
    for lead in leads:
        if lead.status not in {LeadStatus.WON, LeadStatus.LOST}:
            continue
        ca = _normalize_timestamp(lead.created_at)
        ua = _normalize_timestamp(lead.updated_at)
        if ca and ua:
            closed_cycle_days.append((ua - ca).total_seconds() / 86400)

    return {
        "total_leads": total_leads,
        "new_today": new_today,
        "qualified": qualified,
        "approved": approved,
        "contacted": contacted,
        "replied": replied,
        "meetings": meetings,
        "won": won,
        "lost": lost,
        "suppressed": suppressed,
        "avg_score": round(_safe_average(scored_values), 1),
        "conversion_rate": round(_safe_rate(won, contacted), 4),
        "open_rate": round(_safe_rate(opened, contacted), 4),
        "reply_rate": round(_safe_rate(replied, contacted), 4),
        "positive_reply_rate": round(_safe_rate(meetings, replied), 4),
        "meeting_rate": round(_safe_rate(meetings, contacted), 4),
        "pipeline_velocity": round(_safe_average(closed_cycle_days), 1),
        "last_lead_at": _last_lead_at(db),
    }


def get_pipeline_breakdown(db: Session) -> list[dict]:
    stage_counts = []
    for stage, label, color in PIPELINE_STAGE_META:
        count = (
            db.execute(
                select(sa_func.count(Lead.id)).where(_status_at_or_beyond_filter(stage))
            ).scalar()
            or 0
        )
        stage_counts.append({"stage": stage, "label": label, "count": count, "color": color})

    first_count = stage_counts[0]["count"] if stage_counts else 0
    for stage in stage_counts:
        stage["percentage"] = (
            round(_safe_rate(stage["count"], first_count), 4) if first_count else 0.0
        )
    return stage_counts


def _status_at_or_beyond_filter(stage: LeadStatus):
    """Return a SQL WHERE clause: lead has reached this pipeline stage."""
    target_rank = PIPELINE_STAGE_ORDER[stage]
    matching = [s for s, rank in PIPELINE_STAGE_ORDER.items() if rank >= target_rank]
    if target_rank <= PIPELINE_STAGE_ORDER.get(LeadStatus.CONTACTED, 99):
        matching.append(LeadStatus.LOST)
    return Lead.status.in_(matching)


def get_time_series(db: Session, days: int = 30) -> list[dict]:
    today = _now_utc().date()
    start_date = today - timedelta(days=max(days - 1, 0))
    start_datetime = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)

    timeline = {
        (start_date + timedelta(days=offset)).isoformat(): {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "leads": 0,
            "outreach": 0,
            "replies": 0,
            "conversions": 0,
        }
        for offset in range(days)
    }

    # Leads per day via SQL GROUP BY
    lead_date = sa_func.date(Lead.created_at).label("d")
    lead_rows = db.execute(
        select(lead_date, sa_func.count(Lead.id))
        .where(Lead.created_at >= start_datetime)
        .group_by(lead_date)
    ).all()
    for d, cnt in lead_rows:
        key = str(d)
        if key in timeline:
            timeline[key]["leads"] = cnt

    for draft in _load_sent_drafts(db, since=start_datetime):
        key = _date_key(draft.sent_at)
        if key in timeline:
            timeline[key]["outreach"] += 1

    for log in _load_logs(db, since=start_datetime):
        key = _date_key(log.created_at)
        if key not in timeline:
            continue
        if log.action == LogAction.REPLIED:
            timeline[key]["replies"] += 1
        elif log.action == LogAction.WON:
            timeline[key]["conversions"] += 1

    return [timeline[key] for key in sorted(timeline)]


def get_industry_breakdown(db: Session, *, leads: list[Lead] | None = None) -> list[dict]:
    if leads is not None:
        return _industry_breakdown_python(leads)

    contacted_statuses = [
        s
        for s, rank in PIPELINE_STAGE_ORDER.items()
        if rank >= PIPELINE_STAGE_ORDER[LeadStatus.CONTACTED]
    ] + [LeadStatus.LOST]

    industry_col = sa_func.coalesce(Lead.industry, "Sin rubro").label("industry")
    rows = db.execute(
        select(
            industry_col,
            sa_func.count(Lead.id).label("count"),
            sa_func.avg(Lead.score).label("avg_score"),
            sa_func.sum(case((Lead.status.in_(contacted_statuses), 1), else_=0)).label("contacted"),
            sa_func.sum(case((Lead.status == LeadStatus.WON, 1), else_=0)).label("won"),
        ).group_by(industry_col)
    ).all()

    result = []
    for row in rows:
        contacted = row.contacted or 0
        won = row.won or 0
        result.append(
            {
                "industry": row.industry,
                "count": row.count,
                "avg_score": round(float(row.avg_score or 0), 1),
                "conversion_rate": round(_safe_rate(won, contacted), 4),
            }
        )
    return sorted(
        result, key=lambda item: (-item["conversion_rate"], -item["count"], item["industry"])
    )


def _industry_breakdown_python(leads: list[Lead]) -> list[dict]:
    from collections import defaultdict

    buckets: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        buckets[lead.industry or "Sin rubro"].append(lead)
    result = []
    for industry, bucket in buckets.items():
        scored = [lead.score for lead in bucket if lead.score is not None]
        contacted = sum(1 for lead in bucket if _reached_stage(lead.status, LeadStatus.CONTACTED))
        won = sum(1 for lead in bucket if lead.status == LeadStatus.WON)
        result.append(
            {
                "industry": industry,
                "count": len(bucket),
                "avg_score": round(_safe_average(scored), 1),
                "conversion_rate": round(_safe_rate(won, contacted), 4),
            }
        )
    return sorted(
        result, key=lambda item: (-item["conversion_rate"], -item["count"], item["industry"])
    )


def get_city_breakdown(db: Session, *, leads: list[Lead] | None = None) -> list[dict]:
    if leads is not None:
        return _city_breakdown_python(leads)

    contacted_statuses = [
        s
        for s, rank in PIPELINE_STAGE_ORDER.items()
        if rank >= PIPELINE_STAGE_ORDER[LeadStatus.CONTACTED]
    ] + [LeadStatus.LOST]
    replied_statuses = [
        s
        for s, rank in PIPELINE_STAGE_ORDER.items()
        if rank >= PIPELINE_STAGE_ORDER[LeadStatus.REPLIED]
    ]

    city_col = sa_func.coalesce(Lead.city, "Sin ciudad").label("city")
    rows = db.execute(
        select(
            city_col,
            sa_func.count(Lead.id).label("count"),
            sa_func.avg(Lead.score).label("avg_score"),
            sa_func.sum(case((Lead.status.in_(contacted_statuses), 1), else_=0)).label("contacted"),
            sa_func.sum(case((Lead.status.in_(replied_statuses), 1), else_=0)).label("replied"),
        ).group_by(city_col)
    ).all()

    result = []
    for row in rows:
        contacted = row.contacted or 0
        replied = row.replied or 0
        result.append(
            {
                "city": row.city,
                "count": row.count,
                "avg_score": round(float(row.avg_score or 0), 1),
                "reply_rate": round(_safe_rate(replied, contacted), 4),
            }
        )
    return sorted(result, key=lambda item: (-item["reply_rate"], -item["count"], item["city"]))


def _city_breakdown_python(leads: list[Lead]) -> list[dict]:
    from collections import defaultdict

    buckets: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        buckets[lead.city or "Sin ciudad"].append(lead)
    result = []
    for city, bucket in buckets.items():
        scored = [lead.score for lead in bucket if lead.score is not None]
        contacted = sum(1 for lead in bucket if _reached_stage(lead.status, LeadStatus.CONTACTED))
        replied = sum(1 for lead in bucket if _reached_stage(lead.status, LeadStatus.REPLIED))
        result.append(
            {
                "city": city,
                "count": len(bucket),
                "avg_score": round(_safe_average(scored), 1),
                "reply_rate": round(_safe_rate(replied, contacted), 4),
            }
        )
    return sorted(result, key=lambda item: (-item["reply_rate"], -item["count"], item["city"]))


def get_source_performance(db: Session, *, leads: list[Lead] | None = None) -> list[dict]:
    if leads is not None:
        return _source_performance_python(leads)

    contacted_statuses = [
        s
        for s, rank in PIPELINE_STAGE_ORDER.items()
        if rank >= PIPELINE_STAGE_ORDER[LeadStatus.CONTACTED]
    ] + [LeadStatus.LOST]
    replied_statuses = [
        s
        for s, rank in PIPELINE_STAGE_ORDER.items()
        if rank >= PIPELINE_STAGE_ORDER[LeadStatus.REPLIED]
    ]

    source_col = sa_func.coalesce(LeadSource.name, "Unattributed").label("source_name")
    rows = db.execute(
        select(
            source_col,
            sa_func.count(Lead.id).label("leads"),
            sa_func.avg(Lead.score).label("avg_score"),
            sa_func.sum(case((Lead.status.in_(contacted_statuses), 1), else_=0)).label("contacted"),
            sa_func.sum(case((Lead.status.in_(replied_statuses), 1), else_=0)).label("replied"),
            sa_func.sum(case((Lead.status == LeadStatus.WON, 1), else_=0)).label("won"),
        )
        .outerjoin(LeadSource, Lead.source_id == LeadSource.id)
        .group_by(source_col)
    ).all()

    result = []
    for row in rows:
        contacted = row.contacted or 0
        replied = row.replied or 0
        won = row.won or 0
        result.append(
            {
                "source": row.source_name,
                "leads": row.leads,
                "avg_score": round(float(row.avg_score or 0), 1),
                "reply_rate": round(_safe_rate(replied, contacted), 4),
                "conversion_rate": round(_safe_rate(won, contacted), 4),
            }
        )
    return sorted(
        result, key=lambda item: (-item["conversion_rate"], -item["leads"], item["source"])
    )


def _source_performance_python(leads: list[Lead]) -> list[dict]:
    from collections import defaultdict

    buckets: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        source_name = lead.source.name if lead.source else "Unattributed"
        buckets[source_name].append(lead)
    result = []
    for source_name, bucket in buckets.items():
        scored = [lead.score for lead in bucket if lead.score is not None]
        contacted = sum(1 for lead in bucket if _reached_stage(lead.status, LeadStatus.CONTACTED))
        replied = sum(1 for lead in bucket if _reached_stage(lead.status, LeadStatus.REPLIED))
        won = sum(1 for lead in bucket if lead.status == LeadStatus.WON)
        result.append(
            {
                "source": source_name,
                "leads": len(bucket),
                "avg_score": round(_safe_average(scored), 1),
                "reply_rate": round(_safe_rate(replied, contacted), 4),
                "conversion_rate": round(_safe_rate(won, contacted), 4),
            }
        )
    return sorted(
        result, key=lambda item: (-item["conversion_rate"], -item["leads"], item["source"])
    )


def get_recent_activity(db: Session, limit: int = 20) -> list[OutreachLog]:
    return _load_logs(db)[:limit]


def get_ai_health_summary(db: Session) -> dict:
    """Return AI health metrics for the dashboard (last 24 hours)."""
    from app.models.llm_invocation import LLMInvocation

    since = _now_utc() - timedelta(hours=24)

    total = (
        db.query(sa_func.count(LLMInvocation.id)).filter(LLMInvocation.created_at >= since).scalar()
        or 0
    )
    succeeded = (
        db.query(sa_func.count(LLMInvocation.id))
        .filter(LLMInvocation.created_at >= since, LLMInvocation.status == "succeeded")
        .scalar()
        or 0
    )
    fallbacks = (
        db.query(sa_func.count(LLMInvocation.id))
        .filter(LLMInvocation.created_at >= since, LLMInvocation.fallback_used.is_(True))
        .scalar()
        or 0
    )
    avg_latency = (
        db.query(sa_func.avg(LLMInvocation.latency_ms))
        .filter(LLMInvocation.created_at >= since, LLMInvocation.latency_ms.isnot(None))
        .scalar()
    )

    return {
        "approval_rate": round(succeeded / max(total, 1), 2),
        "fallback_rate": round(fallbacks / max(total, 1), 2),
        "avg_latency_ms": round(avg_latency) if avg_latency else None,
        "invocations_24h": total,
    }


def get_pipeline_throughput(db: Session) -> dict:
    """Pipeline throughput metrics for the last 24 hours."""
    from app.models.task_tracking import PipelineRun

    cutoff = _now_utc() - timedelta(hours=24)

    # Pipelines completed in last 24h
    completed = (
        db.query(sa_func.count(PipelineRun.id))
        .filter(
            PipelineRun.status == "succeeded",
            PipelineRun.finished_at >= cutoff,
        )
        .scalar()
        or 0
    )

    failed = (
        db.query(sa_func.count(PipelineRun.id))
        .filter(
            PipelineRun.status == "failed",
            PipelineRun.finished_at >= cutoff,
        )
        .scalar()
        or 0
    )

    # Lead inventory by status
    inventory = {}
    for status in LeadStatus:
        count = db.query(sa_func.count(Lead.id)).filter(Lead.status == status.value).scalar() or 0
        if count > 0:
            inventory[status.value] = count

    return {
        "completed_24h": completed,
        "failed_24h": failed,
        "failure_rate": round(failed / max(completed + failed, 1), 3),
        "lead_inventory": inventory,
    }


def get_investigation_detail(db: Session, lead_id: uuid.UUID) -> dict | None:
    """Return Scout investigation thread for a lead, or None if not found."""
    from app.models.investigation_thread import InvestigationThread

    thread = (
        db.query(InvestigationThread)
        .filter_by(lead_id=lead_id)
        .order_by(InvestigationThread.created_at.desc())
        .first()
    )
    if not thread:
        return None

    return {
        "id": str(thread.id),
        "lead_id": str(thread.lead_id),
        "agent_model": thread.agent_model,
        "tool_calls": thread.tool_calls_json,
        "pages_visited": thread.pages_visited_json,
        "findings": thread.findings_json,
        "loops_used": thread.loops_used,
        "duration_ms": thread.duration_ms,
        "error": thread.error,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
    }
