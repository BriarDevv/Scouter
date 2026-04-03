import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.llm.types import LLMInvocationStatus


class LLMInvocation(Base):
    __tablename__ = "llm_invocations"
    __table_args__ = (
        Index("ix_llm_invocations_prompt_id", "prompt_id"),
        Index("ix_llm_invocations_status", "status"),
        Index("ix_llm_invocations_target_type_target_id", "target_type", "target_id"),
        Index("ix_llm_invocations_correlation_id", "correlation_id"),
        Index("ix_llm_invocations_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    function_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_id: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[LLMInvocationStatus] = mapped_column(
        Enum(LLMInvocationStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pipeline_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
