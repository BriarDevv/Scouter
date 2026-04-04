from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
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
DbSession = Annotated[Session, Depends(get_db)]


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


@router.get("/resource-mode")
def get_resource_mode(db: DbSession):
    """Return current resource mode: DB setting vs runtime (worker) value."""
    from app.core.config import settings as env_settings

    row = get_or_create(db)
    db_value = row.low_resource_mode  # None = use env default
    env_value = env_settings.LOW_RESOURCE_MODE

    # What the DB says (or env fallback)
    desired = db_value if db_value is not None else env_value

    # What workers are actually running with (resolved at celery import)
    try:
        from app.workers.celery_app import _low_resource as runtime_value
    except Exception:
        runtime_value = env_value

    return {
        "db_value": db_value,
        "env_value": env_value,
        "desired": desired,
        "runtime": runtime_value,
        "restart_required": desired != runtime_value,
    }


@router.post("/runtime-mode")
def set_runtime_mode(mode: str, db: DbSession):
    """Apply a runtime mode preset (safe | assisted | auto)."""
    try:
        row = apply_runtime_mode(db, mode)
        return to_response_dict(row)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
