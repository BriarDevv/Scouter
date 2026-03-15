"""Pydantic schemas for Telegram credentials and settings."""

from datetime import datetime

from pydantic import BaseModel


class TelegramCredentialsResponse(BaseModel):
    bot_username: str | None = None
    bot_token_set: bool = False
    chat_id: str | None = None
    webhook_url: str | None = None
    webhook_secret_set: bool = False
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_error: str | None = None
    updated_at: datetime | None = None


class TelegramCredentialsUpdate(BaseModel):
    bot_username: str | None = None
    bot_token: str | None = None
    chat_id: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None

    def to_update_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class TelegramTestResult(BaseModel):
    ok: bool
    error: str | None = None
    bot_username: str | None = None
