from fastapi import APIRouter

from app.api.v1.ai_office import router as ai_office_router
from app.api.v1.briefs import router as briefs_router
from app.api.v1.chat import router as chat_router
from app.api.v1.crawl import router as crawl_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.enrichment import router as enrichment_router
from app.api.v1.leader import router as leader_router
from app.api.v1.leads import router as leads_router
from app.api.v1.mail import router as mail_inbound_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.outreach import router as outreach_router
from app.api.v1.performance import router as performance_router
from app.api.v1.pipelines import router as pipelines_router
from app.api.v1.replies import router as replies_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.settings import router as settings_router
from app.api.v1.suppression import router as suppression_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.territories import router as territories_router
from app.api.v1.whatsapp import router as whatsapp_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(leads_router)
api_router.include_router(leader_router)
api_router.include_router(enrichment_router)
api_router.include_router(scoring_router)
api_router.include_router(settings_router)
api_router.include_router(mail_inbound_router)
api_router.include_router(outreach_router)
api_router.include_router(suppression_router)
api_router.include_router(dashboard_router)
api_router.include_router(performance_router)
api_router.include_router(tasks_router)
api_router.include_router(pipelines_router)
api_router.include_router(reviews_router)
api_router.include_router(replies_router)
api_router.include_router(territories_router)
api_router.include_router(notifications_router)
api_router.include_router(whatsapp_router)
api_router.include_router(telegram_router)
api_router.include_router(crawl_router)
api_router.include_router(chat_router)
api_router.include_router(briefs_router)
api_router.include_router(ai_office_router)
