import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.db.session import get_db
from app.schemas.setup import SetupActionResultResponse, SetupReadinessResponse
from app.services.settings.setup_service import get_setup_readiness, run_setup_action

router = APIRouter(prefix="/setup", tags=["setup"])
DbSession = Annotated[object, Depends(get_db)]

# Simple in-process rate limit for setup actions (1 action per 5 seconds)
_last_action_time: float = 0.0
_ACTION_COOLDOWN_SECONDS = 5.0


@router.get("/readiness", response_model=SetupReadinessResponse)
def readiness(db: DbSession):
    return get_setup_readiness(db)


@router.post("/actions/{action_id}", response_model=SetupActionResultResponse)
def run_action(action_id: str, db: DbSession):
    global _last_action_time  # noqa: PLW0603
    now = time.monotonic()
    if now - _last_action_time < _ACTION_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail="Setup action rate limited. Wait a few seconds before retrying.",
        )
    _last_action_time = now

    try:
        return run_setup_action(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Setup action not found") from exc
