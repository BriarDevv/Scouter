from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.catalog import DEFAULT_ROLE_MODEL_MAP, DEFAULT_SUPPORTED_MODELS, parse_supported_models
from app.llm.roles import LLMRole


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
    # Legacy default runtime model, kept as executor fallback for backward compatibility.
    OLLAMA_MODEL: str = DEFAULT_ROLE_MODEL_MAP[LLMRole.EXECUTOR]
    # Supported local models available for role assignment.
    OLLAMA_SUPPORTED_MODELS: str = ",".join(DEFAULT_SUPPORTED_MODELS)
    OLLAMA_LEADER_MODEL: str = DEFAULT_ROLE_MODEL_MAP[LLMRole.LEADER]
    OLLAMA_EXECUTOR_MODEL: str | None = None
    OLLAMA_REVIEWER_MODEL: str | None = DEFAULT_ROLE_MODEL_MAP[LLMRole.REVIEWER]
    OLLAMA_AGENT_MODEL: str | None = DEFAULT_ROLE_MODEL_MAP[LLMRole.AGENT]
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_REVIEWER_TIMEOUT: int = 360
    OLLAMA_AGENT_TIMEOUT: int = 180
    OLLAMA_MAX_RETRIES: int = 3

    # Crawling
    CRAWLER_RATE_LIMIT_PER_SECOND: float = 1.0
    CRAWLER_TIMEOUT: int = 15
    CRAWLER_MAX_RETRIES: int = 2
    CRAWLER_USER_AGENT: str = "ClawScout/1.0 (research)"

    # Outreach
    OUTREACH_AUTO_SEND: bool = False

    # Mail
    MAIL_PROVIDER: str = "smtp"
    MAIL_ENABLED: bool = False
    MAIL_FROM_EMAIL: str | None = None
    MAIL_FROM_NAME: str = "ClawScout"
    MAIL_REPLY_TO: str | None = None
    MAIL_SMTP_HOST: str | None = None
    MAIL_SMTP_PORT: int = 587
    MAIL_SMTP_USERNAME: str | None = None
    MAIL_SMTP_PASSWORD: str | None = None
    MAIL_SMTP_STARTTLS: bool = True
    MAIL_SMTP_SSL: bool = False
    MAIL_SEND_TIMEOUT: int = 30
    MAIL_INBOUND_PROVIDER: str = "imap"
    MAIL_INBOUND_ENABLED: bool = False
    MAIL_IMAP_HOST: str | None = None
    MAIL_IMAP_PORT: int = 993
    MAIL_IMAP_USERNAME: str | None = None
    MAIL_IMAP_PASSWORD: str | None = None
    MAIL_IMAP_SSL: bool = True
    MAIL_IMAP_MAILBOX: str = "INBOX"
    MAIL_IMAP_SEARCH_CRITERIA: str = "ALL"
    MAIL_INBOUND_SYNC_LIMIT: int = 25
    MAIL_INBOUND_TIMEOUT: int = 30
    MAIL_AUTO_CLASSIFY_INBOUND: bool = False
    MAIL_USE_REVIEWER_FOR_LABELS: str = ""

    # Google Maps
    GOOGLE_MAPS_API_KEY: str | None = None

    # WhatsApp
    WHATSAPP_DRY_RUN: bool = True

    # Kapso (WhatsApp outreach) — uses Platform API (simpler, no phone_number_id needed)
    KAPSO_API_KEY: str | None = None
    KAPSO_BASE_URL: str = "https://app.kapso.ai/api/v1"

    # Telegram
    TELEGRAM_DRY_RUN: bool = True

    # Authentication
    API_KEY: str | None = None  # Set to enable API key auth; None = open (dev only)

    # Rate limiting (API)
    API_RATE_LIMIT: str = "60/minute"
    API_CORS_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001"
    )

    @model_validator(mode="after")
    def validate_ollama_models(self):
        supported_models = set(self.ollama_supported_models)

        configured_models = {
            "OLLAMA_MODEL": self.OLLAMA_MODEL.strip(),
            "OLLAMA_LEADER_MODEL": self.ollama_leader_model,
            "OLLAMA_EXECUTOR_MODEL": self.ollama_executor_model,
            "OLLAMA_REVIEWER_MODEL": self.ollama_reviewer_model,
            "OLLAMA_AGENT_MODEL": self.ollama_agent_model,
        }

        for field_name, model_name in configured_models.items():
            if model_name is None:
                continue
            if model_name not in supported_models:
                raise ValueError(
                    f"{field_name} must be one of {sorted(supported_models)}, got {model_name!r}"
                )
        return self

    @model_validator(mode="after")
    def validate_api_key(self):
        if not self.API_KEY and self.APP_ENV != "development":
            import warnings
            warnings.warn(
                "API_KEY is not set. The API is open without authentication. "
                "Set API_KEY in .env to enable API key auth.",
                stacklevel=2,
            )
        return self

    @model_validator(mode="after")
    def validate_secret_key(self):
        if self.SECRET_KEY == "change-me-to-a-random-secret-key":
            if self.APP_ENV != "development":
                raise ValueError(
                    "SECRET_KEY must be changed from default in non-development environments. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            import warnings
            warnings.warn(
                "SECRET_KEY is still set to the default placeholder. "
                'Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(64))"',
                stacklevel=2,
            )
        return self

    @property
    def ollama_supported_models(self) -> tuple[str, ...]:
        return parse_supported_models(self.OLLAMA_SUPPORTED_MODELS)

    @property
    def ollama_leader_model(self) -> str:
        return self.OLLAMA_LEADER_MODEL.strip()

    @property
    def ollama_executor_model(self) -> str:
        configured = (self.OLLAMA_EXECUTOR_MODEL or "").strip()
        return configured or self.OLLAMA_MODEL.strip()

    @property
    def ollama_reviewer_model(self) -> str | None:
        configured = (self.OLLAMA_REVIEWER_MODEL or "").strip()
        return configured or None

    @property
    def ollama_agent_model(self) -> str | None:
        configured = (self.OLLAMA_AGENT_MODEL or "").strip()
        return configured or None

    @property
    def ollama_models_by_role(self) -> dict[LLMRole, str | None]:
        return {
            LLMRole.LEADER: self.ollama_leader_model,
            LLMRole.EXECUTOR: self.ollama_executor_model,
            LLMRole.REVIEWER: self.ollama_reviewer_model,
            LLMRole.AGENT: self.ollama_agent_model,
        }

    @property
    def api_cors_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip()
            for origin in self.API_CORS_ORIGINS.split(",")
            if origin.strip()
        )

    @property
    def mail_use_reviewer_for_labels(self) -> tuple[str, ...]:
        return tuple(
            label.strip()
            for label in self.MAIL_USE_REVIEWER_FOR_LABELS.split(",")
            if label.strip()
        )


settings = Settings()
