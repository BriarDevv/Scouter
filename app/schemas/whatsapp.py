"""Pydantic schemas for WhatsApp credentials and settings."""

from datetime import datetime

from pydantic import BaseModel


class WhatsAppCredentialsResponse(BaseModel):
    provider: str
    phone_number: str | None = None
    api_key_set: bool = False
    webhook_url: str | None = None
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_error: str | None = None
    updated_at: datetime | None = None


class WhatsAppCredentialsUpdate(BaseModel):
    provider: str | None = None
    phone_number: str | None = None
    api_key: str | None = None
    webhook_url: str | None = None

    def to_update_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class WhatsAppTestResult(BaseModel):
    ok: bool
    error: str | None = None
    provider: str | None = None
