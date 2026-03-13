from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_OLLAMA_SUPPORTED_MODELS = (
    "qwen3.5:4b",
    "qwen3.5:9b",
    "qwen3.5:27b",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "ClawScout"
    APP_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-to-a-random-secret-key"

    # Database
    DATABASE_URL: str = "postgresql://clawscout:changeme@localhost:5432/clawscout"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Ollama / LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Current default runtime model. Future role-based routing can override this.
    OLLAMA_MODEL: str = "qwen3.5:9b"
    # Reserved for future model selection by role, kept simple as CSV for now.
    OLLAMA_SUPPORTED_MODELS: str = ",".join(DEFAULT_OLLAMA_SUPPORTED_MODELS)
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_MAX_RETRIES: int = 3

    # Crawling
    CRAWLER_RATE_LIMIT_PER_SECOND: float = 1.0
    CRAWLER_TIMEOUT: int = 30
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_USER_AGENT: str = "ClawScout/1.0 (research)"

    # Outreach
    OUTREACH_AUTO_SEND: bool = False

    # Rate limiting (API)
    API_RATE_LIMIT: str = "60/minute"
    API_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def ollama_supported_models(self) -> tuple[str, ...]:
        return tuple(
            model.strip()
            for model in self.OLLAMA_SUPPORTED_MODELS.split(",")
            if model.strip()
        )

    @property
    def api_cors_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip()
            for origin in self.API_CORS_ORIGINS.split(",")
            if origin.strip()
        )


settings = Settings()
