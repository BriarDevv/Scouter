from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_session
from app.schemas.operational_settings import (
    OperationalSettingsResponse,
    OperationalSettingsUpdate,
)
from app.services.settings.operational_settings_service import (
    apply_runtime_mode,
    get_or_create,
    to_response_dict,
    update_operational_settings,
)

router = APIRouter()
DbSession = Annotated[object, Depends(get_session)]


@router.get("/operational", response_model=OperationalSettingsResponse)
def get_operational(db: DbSession):
    """Return the current operational settings."""
    row = get_or_create(db)
    return to_response_dict(row)


@router.patch("/operational", response_model=OperationalSettingsResponse)
def patch_operational(body: OperationalSettingsUpdate, db: DbSession):
    """Partial-update operational settings. Only sent fields are modified."""
    updates = body.to_update_dict()
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update provided.")
    row = update_operational_settings(db, updates)
    return to_response_dict(row)


@router.post("/runtime-mode")
def set_runtime_mode(mode: str, db: DbSession):
    """Apply a runtime mode preset (safe | assisted | auto)."""
    try:
        row = apply_runtime_mode(db, mode)
        return to_response_dict(row)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
