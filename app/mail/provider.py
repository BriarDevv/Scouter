from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MailSendRequest:
    recipient_email: str
    subject: str
    body: str
    from_email: str
    from_name: str
    reply_to: str | None
    timeout_seconds: int
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_ssl: bool | None = None
    smtp_starttls: bool | None = None
    in_reply_to: str | None = None
    references_raw: str | None = None


@dataclass(frozen=True)
class MailSendResult:
    provider: str
    provider_message_id: str | None
    recipient_email: str
    sent_at: datetime


class MailProviderError(RuntimeError):
    """Raised when the provider cannot send a message."""


class MailProvider(Protocol):
    name: str

    def send_email(self, request: MailSendRequest) -> MailSendResult: ...
