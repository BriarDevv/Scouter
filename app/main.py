from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.API_RATE_LIMIT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", env=settings.APP_ENV)
    yield
    logger.info("app_shutting_down")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Private lead prospecting system for web development services",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS for dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.api_cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.1.0"}
