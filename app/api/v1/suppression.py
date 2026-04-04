import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.suppression import SuppressionCreate, SuppressionResponse
from app.services.suppression_service import (
    add_to_suppression_list,
    list_suppression,
    remove_from_suppression,
)

router = APIRouter(prefix="/suppression", tags=["suppression"])


@router.post("", response_model=SuppressionResponse, status_code=201)
def add(data: SuppressionCreate, db: Session = Depends(get_db)):
    """Add an email/domain/phone to the suppression list."""
    if not data.email and not data.domain and not data.phone:
        raise HTTPException(status_code=422, detail="At least one of email, domain, or phone is required")
    entry = add_to_suppression_list(db, data)
    return entry


@router.get("", response_model=list[SuppressionResponse])
def list_all(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all suppression entries."""
    return list_suppression(db, page=page, page_size=page_size)


@router.delete("/{entry_id}", status_code=204)
def remove(entry_id: uuid.UUID, db: Session = Depends(get_db)):
    """Remove an entry from the suppression list."""
    if not remove_from_suppression(db, entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")
