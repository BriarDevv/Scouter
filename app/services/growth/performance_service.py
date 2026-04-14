"""Territory & category performance aggregation for the Growth Intelligence Agent.

This module computes and persists rolling-window metrics per Territory and
exposes on-demand category (niche) rollups. Snapshots are written by the
weekly Celery task (`app.workers.growth_tasks.task_snapshot_territory_performance`)
but callers may also compute fresh metrics without persisting.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadStatus
from app.models.territory import Territory
from app.models.territory_performance import TerritoryPerformance

# Pipeline ordering mirrors the territory_service module (kept local to avoid
# cross-domain imports between service packages).
_PIPELINE_ORDER: dict[LeadStatus, int] = {
    LeadStatus.NEW: 0,
    LeadStatus.ENRICHED: 1,
    LeadStatus.SCORED: 2,
    LeadStatus.QUALIFIED: 3,
    LeadStatus.DRAFT_READY: 4,
    LeadStatus.APPROVED: 5,
    LeadStatus.CONTACTED: 6,
    LeadStatus.OPENED: 7,
    LeadStatus.REPLIED: 8,
    LeadStatus.MEETING: 9,
    LeadStatus.WON: 10,
}

# LOST/SUPPRESSED are terminal; treat LOST as having reached CONTACTED because a
# lead must be contacted before it can be marked lost. SUPPRESSED stays None.
_STATUS_FALLBACK: dict[LeadStatus, int | None] = {
    LeadStatus.LOST: _PIPELINE_ORDER[LeadStatus.CONTACTED],
    LeadStatus.SUPPRESSED: None,
}


def _stage_rank(status: LeadStatus) -> int | None:
    if status in _PIPELINE_ORDER:
        return _PIPELINE_ORDER[status]
    return _STATUS_FALLBACK.get(status)


def _reached_stage(status: LeadStatus, stage: LeadStatus) -> bool:
    current = _stage_rank(status)
    target = _PIPELINE_ORDER[stage]
    return current is not None and current >= target


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _safe_average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _period_bounds(period_days: int) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return now - timedelta(days=period_days), now


def _leads_for_cities(
    db: Session,
    cities: list[str],
    *,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Lead]:
    if not cities:
        return []
    stmt = select(Lead).where(Lead.city.in_(cities))
    if start is not None:
        stmt = stmt.where(Lead.created_at >= start)
    if end is not None:
        stmt = stmt.where(Lead.created_at < end)
    return list(db.execute(stmt).scalars().all())


def _compute_metrics(leads: list[Lead]) -> dict:
    """Aggregate pipeline metrics for an iterable of leads."""
    leads_created = len(leads)
    qualified = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.QUALIFIED))
    contacted = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.CONTACTED))
    won = sum(1 for lead in leads if lead.status == LeadStatus.WON)
    lost = sum(1 for lead in leads if lead.status == LeadStatus.LOST)
    scores = [lead.score for lead in leads if lead.score is not None]

    return {
        "leads_created": leads_created,
        "leads_qualified": qualified,
        "leads_contacted": contacted,
        "leads_won": won,
        "leads_lost": lost,
        "conversion_rate": _safe_rate(won, leads_created),
        "avg_score": _safe_average(scores),
    }


def snapshot_territory_performance(
    db: Session, territory: Territory, period_days: int = 30
) -> TerritoryPerformance:
    """Compute a performance snapshot for a territory and persist it.

    The snapshot covers leads whose `created_at` falls in the last
    `period_days`. The record is flushed (not committed) — callers are
    responsible for managing the transaction boundary.
    """
    period_start, period_end = _period_bounds(period_days)
    leads = _leads_for_cities(db, territory.cities, start=period_start, end=period_end)
    metrics = _compute_metrics(leads)

    # Dedup count comes from the territory's last crawl, expressed as a ratio.
    duplicates = 0
    if territory.last_dup_ratio is not None and metrics["leads_created"] > 0:
        duplicates = int(round(territory.last_dup_ratio * metrics["leads_created"]))

    snapshot = TerritoryPerformance(
        territory_id=territory.id,
        period_start=period_start,
        period_end=period_end,
        leads_created=metrics["leads_created"],
        leads_qualified=metrics["leads_qualified"],
        leads_contacted=metrics["leads_contacted"],
        leads_won=metrics["leads_won"],
        leads_lost=metrics["leads_lost"],
        total_duplicates=duplicates,
        conversion_rate=metrics["conversion_rate"],
        avg_score=metrics["avg_score"],
    )
    db.add(snapshot)
    db.flush()
    db.refresh(snapshot)
    return snapshot


def get_territory_performance(db: Session, territory: Territory, period_days: int = 30) -> dict:
    """Return fresh performance metrics for a territory.

    Prefers the most recent persisted snapshot when it covers the requested
    window; otherwise computes metrics on-the-fly without persisting.
    """
    period_start, period_end = _period_bounds(period_days)

    latest_stmt = (
        select(TerritoryPerformance)
        .where(
            TerritoryPerformance.territory_id == territory.id,
            TerritoryPerformance.period_end >= period_start,
        )
        .order_by(TerritoryPerformance.period_end.desc())
        .limit(1)
    )
    latest = db.execute(latest_stmt).scalars().first()
    if latest is not None:
        return _snapshot_to_dict(latest, territory)

    leads = _leads_for_cities(db, territory.cities, start=period_start, end=period_end)
    metrics = _compute_metrics(leads)
    return {
        "territory_id": territory.id,
        "territory_name": territory.name,
        "period_start": period_start,
        "period_end": period_end,
        "total_duplicates": 0,
        **metrics,
    }


def get_all_territory_performance(db: Session, period_days: int = 30) -> list[dict]:
    """Return performance dicts for every active territory."""
    stmt = select(Territory).where(Territory.is_active.is_(True)).order_by(Territory.name)
    territories = list(db.execute(stmt).scalars().all())
    return [get_territory_performance(db, t, period_days=period_days) for t in territories]


def get_category_performance(
    db: Session, territory: Territory | None = None, period_days: int = 30
) -> list[dict]:
    """Return per-category (niche) performance for the given window.

    Category is derived from `Lead.industry`. When `territory` is provided the
    query is restricted to leads whose city is in `territory.cities`.
    Categories with no leads in the window are omitted. Results are sorted by
    `leads_created` descending for easy inspection.
    """
    period_start, period_end = _period_bounds(period_days)

    stmt = select(Lead).where(
        Lead.industry.is_not(None),
        Lead.created_at >= period_start,
        Lead.created_at < period_end,
    )
    if territory is not None:
        if not territory.cities:
            return []
        stmt = stmt.where(Lead.city.in_(territory.cities))

    leads = list(db.execute(stmt).scalars().all())
    buckets: dict[str, list[Lead]] = {}
    for lead in leads:
        category = lead.industry or ""
        if not category:
            continue
        buckets.setdefault(category, []).append(lead)

    results: list[dict] = []
    for category, group in buckets.items():
        metrics = _compute_metrics(group)
        results.append(
            {
                "category": category,
                "territory_id": territory.id if territory is not None else None,
                "period_start": period_start,
                "period_end": period_end,
                **metrics,
            }
        )
    results.sort(key=lambda item: item["leads_created"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _snapshot_to_dict(snapshot: TerritoryPerformance, territory: Territory) -> dict:
    return {
        "territory_id": snapshot.territory_id,
        "territory_name": territory.name,
        "period_start": snapshot.period_start,
        "period_end": snapshot.period_end,
        "leads_created": snapshot.leads_created,
        "leads_qualified": snapshot.leads_qualified,
        "leads_contacted": snapshot.leads_contacted,
        "leads_won": snapshot.leads_won,
        "leads_lost": snapshot.leads_lost,
        "total_duplicates": snapshot.total_duplicates,
        "conversion_rate": snapshot.conversion_rate,
        "avg_score": snapshot.avg_score,
    }


__all__ = [
    "get_all_territory_performance",
    "get_category_performance",
    "get_territory_performance",
    "snapshot_territory_performance",
]
