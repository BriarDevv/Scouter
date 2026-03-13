from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class InboundMailMessage:
    provider: str
    provider_mailbox: str
    provider_message_id: str | None
    message_id: str | None
    in_reply_to: str | None
    references_raw: str | None
    from_email: str | None
    from_name: str | None
    to_email: str | None
    subject: str | None
    body_text: str | None
    body_snippet: str | None
    received_at: datetime | None
    raw_metadata: dict[str, Any]


class InboundMailProviderError(RuntimeError):
    """Raised when inbound mail cannot be fetched from the configured provider."""


class InboundMailProvider(Protocol):
    name: str

    def list_messages(self, *, limit: int) -> list[InboundMailMessage]:
        ...
