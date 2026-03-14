from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session, joinedload

from app.models.lead import Lead, LeadStatus
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


def _load_leads(db: Session) -> list[Lead]:
    stmt = select(Lead).options(joinedload(Lead.source))
    return list(db.execute(stmt).scalars().unique().all())


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

def get_dashboard_stats(db: Session, *, leads: list[Lead] | None = None) -> dict:
    leads = leads if leads is not None else _load_leads(db)
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
        created_at = _normalize_timestamp(lead.created_at)
        updated_at = _normalize_timestamp(lead.updated_at)
        if created_at and updated_at:
            closed_cycle_days.append((updated_at - created_at).total_seconds() / 86400)

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
    leads = _load_leads(db)
    stage_counts = []
    for stage, label, color in PIPELINE_STAGE_META:
        count = sum(1 for lead in leads if _reached_stage(lead.status, stage))
        stage_counts.append({"stage": stage, "label": label, "count": count, "color": color})

    first_count = stage_counts[0]["count"] if stage_counts else 0
    for stage in stage_counts:
        stage["percentage"] = round(_safe_rate(stage["count"], first_count), 4) if first_count else 0.0
    return stage_counts


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

    for lead in _load_leads(db):
        key = _date_key(lead.created_at)
        if key in timeline:
            timeline[key]["leads"] += 1

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
    leads = leads if leads is not None else _load_leads(db)
    buckets: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        buckets[lead.industry or "Sin rubro"].append(lead)

    result = []
    for industry, leads in buckets.items():
        scored = [lead.score for lead in leads if lead.score is not None]
        contacted = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.CONTACTED))
        won = sum(1 for lead in leads if lead.status == LeadStatus.WON)
        result.append(
            {
                "industry": industry,
                "count": len(leads),
                "avg_score": round(_safe_average(scored), 1),
                "conversion_rate": round(_safe_rate(won, contacted), 4),
            }
        )
    return sorted(result, key=lambda item: (-item["conversion_rate"], -item["count"], item["industry"]))


def get_city_breakdown(db: Session, *, leads: list[Lead] | None = None) -> list[dict]:
    leads = leads if leads is not None else _load_leads(db)
    buckets: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        buckets[lead.city or "Sin ciudad"].append(lead)

    result = []
    for city, leads in buckets.items():
        scored = [lead.score for lead in leads if lead.score is not None]
        contacted = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.CONTACTED))
        replied = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.REPLIED))
        result.append(
            {
                "city": city,
                "count": len(leads),
                "avg_score": round(_safe_average(scored), 1),
                "reply_rate": round(_safe_rate(replied, contacted), 4),
            }
        )
    return sorted(result, key=lambda item: (-item["reply_rate"], -item["count"], item["city"]))


def get_source_performance(db: Session, *, leads: list[Lead] | None = None) -> list[dict]:
    leads = leads if leads is not None else _load_leads(db)
    buckets: dict[str, list[Lead]] = defaultdict(list)
    for lead in leads:
        source_name = lead.source.name if lead.source else "Unattributed"
        buckets[source_name].append(lead)

    result = []
    for source_name, leads in buckets.items():
        scored = [lead.score for lead in leads if lead.score is not None]
        contacted = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.CONTACTED))
        replied = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.REPLIED))
        won = sum(1 for lead in leads if lead.status == LeadStatus.WON)
        result.append(
            {
                "source": source_name,
                "leads": len(leads),
                "avg_score": round(_safe_average(scored), 1),
                "reply_rate": round(_safe_rate(replied, contacted), 4),
                "conversion_rate": round(_safe_rate(won, contacted), 4),
            }
        )
    return sorted(result, key=lambda item: (-item["conversion_rate"], -item["leads"], item["source"]))


def get_recent_activity(db: Session, limit: int = 20) -> list[OutreachLog]:
    return _load_logs(db)[:limit]
