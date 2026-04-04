from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_session
from app.schemas.setup import SetupActionResultResponse, SetupReadinessResponse
from app.services.setup_service import get_setup_readiness, run_setup_action

router = APIRouter(prefix="/setup", tags=["setup"])
DbSession = Annotated[object, Depends(get_session)]


@router.get("/readiness", response_model=SetupReadinessResponse)
def readiness(db: DbSession):
    return get_setup_readiness(db)


@router.post("/actions/{action_id}", response_model=SetupActionResultResponse)
def run_action(action_id: str):
    try:
        return run_setup_action(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Setup action not found") from exc
