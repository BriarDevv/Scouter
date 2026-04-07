"""Territory service — CRUD + stats aggregation for geographic territories."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadStatus
from app.models.territory import Territory
from app.schemas.territory import TerritoryCreate, TerritoryUpdate


# ── Helpers ─────────────────────────────────────────────

_QUALIFIED_STAGE_RANK = 3  # LeadStatus.QUALIFIED index in pipeline

_PIPELINE_ORDER = {
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

_STATUS_FALLBACK = {
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
    return numerator / denominator


def _safe_average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


# ── CRUD ────────────────────────────────────────────────

def create_territory(db: Session, data: TerritoryCreate) -> Territory:
    territory = Territory(
        name=data.name,
        description=data.description,
        color=data.color,
        cities=data.cities,
        is_active=data.is_active,
    )
    db.add(territory)
    db.flush()
    db.refresh(territory)
    return territory


def get_territory(db: Session, territory_id: UUID) -> Territory | None:
    return db.get(Territory, territory_id)


def list_territories(db: Session) -> list[Territory]:
    stmt = select(Territory).order_by(Territory.name)
    return list(db.execute(stmt).scalars().all())


def update_territory(db: Session, territory_id: UUID, data: TerritoryUpdate) -> Territory | None:
    territory = db.get(Territory, territory_id)
    if territory is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(territory, field, value)
    db.flush()
    db.refresh(territory)
    return territory


def delete_territory(db: Session, territory_id: UUID) -> bool:
    territory = db.get(Territory, territory_id)
    if territory is None:
        return False
    db.delete(territory)
    db.flush()
    return True


# ── Stats ───────────────────────────────────────────────

def _get_leads_in_cities(db: Session, cities: list[str]) -> list[Lead]:
    if not cities:
        return []
    stmt = select(Lead).where(Lead.city.in_(cities))
    return list(db.execute(stmt).scalars().all())


def get_territory_stats(db: Session, territory: Territory) -> dict:
    leads = _get_leads_in_cities(db, territory.cities)
    scored = [lead.score for lead in leads if lead.score is not None]
    qualified = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.QUALIFIED))
    contacted = sum(1 for lead in leads if _reached_stage(lead.status, LeadStatus.CONTACTED))
    won = sum(1 for lead in leads if lead.status == LeadStatus.WON)

    return {
        "lead_count": len(leads),
        "avg_score": round(_safe_average(scored), 1),
        "qualified_count": qualified,
        "conversion_rate": round(_safe_rate(won, contacted), 4),
    }


def get_territory_with_stats(db: Session, territory: Territory) -> dict:
    stats = get_territory_stats(db, territory)
    territory_dict = {
        "id": territory.id,
        "name": territory.name,
        "description": territory.description,
        "color": territory.color,
        "cities": territory.cities,
        "is_active": territory.is_active,
        "created_at": territory.created_at,
        "updated_at": territory.updated_at,
    }
    return {**territory_dict, **stats}


def get_all_territories_with_stats(db: Session) -> list[dict]:
    territories = list_territories(db)
    return [get_territory_with_stats(db, t) for t in territories]
