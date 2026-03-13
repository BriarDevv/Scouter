from fastapi import APIRouter, Depends

from app.api.deps import get_session
from app.schemas.settings import LLMSettingsResponse, MailSettingsResponse
from app.services.settings_service import get_llm_settings, get_mail_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMSettingsResponse)
def llm_settings():
    """Return the active LLM configuration used by ClawScout."""
    return get_llm_settings()


@router.get("/mail", response_model=MailSettingsResponse)
def mail_settings(db=Depends(get_session)):
    """Return the effective non-sensitive mail configuration used by ClawScout."""
    return get_mail_settings(db)
