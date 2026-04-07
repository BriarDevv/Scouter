"""Pydantic schemas for mail credentials."""

from pydantic import BaseModel


class MailCredentialsUpdate(BaseModel):
    """Partial update — all fields optional. Passwords accepted but never returned."""

    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None  # write-only
    smtp_ssl: bool | None = None
    smtp_starttls: bool | None = None

    imap_host: str | None = None
    imap_port: int | None = None
    imap_username: str | None = None
    imap_password: str | None = None  # write-only
    imap_ssl: bool | None = None

    def to_update_dict(self) -> dict:
        """Return only fields explicitly set (including None to clear them)."""
        dumped = self.model_dump()
        return {k: dumped[k] for k in self.model_fields_set}


class MailCredentialsResponse(BaseModel):
    """Response — passwords NEVER exposed, replaced by *_password_set bool."""

    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password_set: bool
    smtp_ssl: bool
    smtp_starttls: bool

    imap_host: str | None
    imap_port: int
    imap_username: str | None
    imap_password_set: bool
    imap_ssl: bool

    smtp_last_test_at: str | None
    smtp_last_test_ok: bool | None
    smtp_last_test_error: str | None

    imap_last_test_at: str | None
    imap_last_test_ok: bool | None
    imap_last_test_error: str | None

    updated_at: str | None


class ConnectionTestResult(BaseModel):
    ok: bool
    error: str | None = None
    sample_count: int | None = None


class SetupStepStatus(BaseModel):
    id: str
    label: str
    status: str  # "complete" | "incomplete" | "warning" | "pending"
    detail: str | None = None
    action: str | None = None  # CTA text if actionable


class SetupStatusResponse(BaseModel):
    steps: list[SetupStepStatus]
    overall: str  # "ready" | "incomplete" | "warning"
    ready_to_send: bool
    ready_to_receive: bool
