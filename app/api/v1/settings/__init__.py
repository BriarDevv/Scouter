from fastapi import APIRouter

from app.api.v1.settings.credentials import router as credentials_router
from app.api.v1.settings.messaging import router as messaging_router
from app.api.v1.settings.operational import router as operational_router
from app.api.v1.settings.readonly import router as readonly_router

router = APIRouter(prefix="/settings", tags=["settings"])
router.include_router(readonly_router)
router.include_router(operational_router)
router.include_router(credentials_router)
router.include_router(messaging_router)
