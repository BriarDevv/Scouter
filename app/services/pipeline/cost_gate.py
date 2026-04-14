"""Daily LLM budget kill-switch.

Sums today's usd_cost_estimated across llm_invocations rows and compares
to OperationalSettings.daily_usd_budget. Returns True if under-budget or
budget is None (unlimited); False when over-budget.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.llm_invocation import LLMInvocation
from app.models.settings import OperationalSettings

logger = get_logger(__name__)

# Emit a warning when daily spend crosses this fraction of budget.
_WARN_THRESHOLD = 0.8


def get_today_cost_usd(db: Session) -> float:
    """Sum usd_cost_estimated of LLMInvocation rows created UTC-today."""
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.execute(
        select(func.coalesce(func.sum(LLMInvocation.usd_cost_estimated), 0.0)).where(
            LLMInvocation.created_at >= today_start
        )
    ).scalar_one()
    return float(total or 0.0)


def check_daily_budget(db: Session) -> bool:
    """Return True if the pipeline is allowed to spend more today.

    - budget is None -> unlimited, return True
    - today_cost < budget -> True (and warn if >80%)
    - today_cost >= budget -> False
    """
    ops = db.get(OperationalSettings, 1)
    budget = getattr(ops, "daily_usd_budget", None) if ops else None
    if budget is None:
        return True

    today_cost = get_today_cost_usd(db)
    if today_cost >= budget:
        logger.warning(
            "daily_budget_exceeded",
            today_cost_usd=round(today_cost, 4),
            daily_budget_usd=budget,
        )
        return False

    if today_cost >= budget * _WARN_THRESHOLD:
        logger.warning(
            "daily_budget_warn_80pct",
            today_cost_usd=round(today_cost, 4),
            daily_budget_usd=budget,
            pct=round((today_cost / budget) * 100, 1),
        )
    return True
