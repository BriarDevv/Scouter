from fastapi import APIRouter

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.enrichment import router as enrichment_router
from app.api.v1.leads import router as leads_router
from app.api.v1.outreach import router as outreach_router
from app.api.v1.performance import router as performance_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.suppression import router as suppression_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(leads_router)
api_router.include_router(enrichment_router)
api_router.include_router(scoring_router)
api_router.include_router(outreach_router)
api_router.include_router(suppression_router)
api_router.include_router(dashboard_router)
api_router.include_router(performance_router)
