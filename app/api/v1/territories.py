"""Territory CRUD + analytics endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.schemas.territory import (
    TerritoryCreate,
    TerritoryResponse,
    TerritoryUpdate,
    TerritoryWithStats,
)
from app.services.territory_service import (
    create_territory,
    delete_territory,
    get_all_territories_with_stats,
    get_territory,
    get_territory_with_stats,
    list_territories,
    update_territory,
    _get_leads_in_cities,
)
from app.schemas.lead import LeadResponse

router = APIRouter(prefix="/territories", tags=["territories"])


@router.get("", response_model=list[TerritoryWithStats])
def list_all(db: Session = Depends(get_session)):
    """Listar todos los territorios con estadísticas."""
    return get_all_territories_with_stats(db)


@router.post("", response_model=TerritoryResponse, status_code=201)
def create(data: TerritoryCreate, db: Session = Depends(get_session)):
    """Crear un nuevo territorio."""
    return create_territory(db, data)


@router.get("/{territory_id}", response_model=TerritoryWithStats)
def get_one(territory_id: UUID, db: Session = Depends(get_session)):
    """Obtener un territorio con sus estadísticas."""
    territory = get_territory(db, territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territorio no encontrado")
    return get_territory_with_stats(db, territory)


@router.patch("/{territory_id}", response_model=TerritoryResponse)
def patch(territory_id: UUID, data: TerritoryUpdate, db: Session = Depends(get_session)):
    """Actualizar un territorio existente."""
    territory = update_territory(db, territory_id, data)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territorio no encontrado")
    return territory


@router.delete("/{territory_id}", status_code=204)
def remove(territory_id: UUID, db: Session = Depends(get_session)):
    """Eliminar un territorio."""
    if not delete_territory(db, territory_id):
        raise HTTPException(status_code=404, detail="Territorio no encontrado")


@router.get("/{territory_id}/leads", response_model=list[LeadResponse])
def territory_leads(
    territory_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
):
    """Obtener los leads dentro de las ciudades del territorio."""
    territory = get_territory(db, territory_id)
    if territory is None:
        raise HTTPException(status_code=404, detail="Territorio no encontrado")
    leads = _get_leads_in_cities(db, territory.cities)
    return leads[:limit]
