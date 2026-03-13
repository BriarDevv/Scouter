from pydantic import BaseModel


class RoleModelDefaultsResponse(BaseModel):
    leader: str
    executor: str
    reviewer: str | None


class LLMSettingsResponse(BaseModel):
    provider: str
    base_url: str
    read_only: bool
    editable: bool
    leader_model: str
    executor_model: str
    reviewer_model: str | None
    supported_models: list[str]
    default_role_models: RoleModelDefaultsResponse
    legacy_executor_fallback_model: str
    legacy_executor_fallback_active: bool
    timeout_seconds: int
    max_retries: int


class MailSyncCountsResponse(BaseModel):
    fetched: int
    new: int
    deduplicated: int
    matched: int
    unmatched: int


class MailLastSyncResponse(BaseModel):
    status: str
    at: str | None
    counts: MailSyncCountsResponse
    error: str | None


class OutboundMailSettingsResponse(BaseModel):
    enabled: bool
    provider: str
    configured: bool
    ready: bool
    from_email: str | None
    from_name: str
    reply_to: str | None
    send_timeout_seconds: int
    require_approved_drafts: bool
    missing_requirements: list[str]


class InboundMailSettingsResponse(BaseModel):
    enabled: bool
    provider: str
    configured: bool
    ready: bool
    account: str | None
    mailbox: str
    sync_limit: int
    timeout_seconds: int
    search_criteria: str
    auto_classify_inbound: bool
    use_reviewer_for_labels: list[str]
    last_sync: MailLastSyncResponse | None
    missing_requirements: list[str]


class MailHealthResponse(BaseModel):
    configured: bool
    enabled: bool
    outbound_ready: bool
    inbound_ready: bool
    last_sync_status: str | None
    last_sync_at: str | None


class MailSettingsResponse(BaseModel):
    read_only: bool
    editable: bool
    outbound: OutboundMailSettingsResponse
    inbound: InboundMailSettingsResponse
    health: MailHealthResponse
