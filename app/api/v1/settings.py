from fastapi import APIRouter

from app.schemas.settings import LLMSettingsResponse
from app.services.settings_service import get_llm_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMSettingsResponse)
def llm_settings():
    """Return the active LLM configuration used by ClawScout."""
    return get_llm_settings()
