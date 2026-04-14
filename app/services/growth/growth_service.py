"""Growth Intelligence orchestrator — state collection, decision, execution.

The Growth Agent is invoked periodically (or reactively when territories
saturate) to pick the next expansion strategy. This module wires the three
stages together:

1. `get_growth_state(db)` — collect all data the agent needs to decide
2. `decide_growth_strategy(state)` — LLM call that returns a structured decision
3. `execute_growth_decision(db, decision)` — apply the decision to the system

Every decision is logged to `growth_decision_logs` for later auditing and
learning.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.crawlers.google_maps_crawler import DEFAULT_CATEGORIES
from app.llm.contracts import GrowthDecision
from app.llm.invocations.growth import decide_growth_strategy
from app.models.growth_decision import GrowthDecisionLog
from app.models.task_tracking import PipelineRun
from app.models.territory import Territory
from app.services.growth.adjacency import get_uncovered_cities
from app.services.growth.performance_service import get_all_territory_performance

logger = get_logger(__name__)


def get_growth_state(db: Session) -> dict:
    """Collect all data the Growth Agent needs to decide.

    Returns a dict with:
    - saturated_territories: list of saturated territory summaries
    - territory_performance: list of performance dicts (30-day window)
    - available_cities: cities not yet covered by any active territory
    - current_categories: crawler categories in use
    - pipeline_activity: recent run counts (success/failure, last 24h)
    """
    # Saturated territories (flagged by the crawl workflow)
    saturated_stmt = select(Territory).where(
        Territory.is_active.is_(True), Territory.is_saturated.is_(True)
    )
    saturated = list(db.execute(saturated_stmt).scalars().all())
    saturated_summary = [
        {
            "territory_id": str(t.id),
            "name": t.name,
            "cities": t.cities or [],
            "crawl_count": t.crawl_count,
            "last_dup_ratio": t.last_dup_ratio,
        }
        for t in saturated
    ]

    # Territory performance (30-day window)
    performance = get_all_territory_performance(db, period_days=30)
    performance_summary = [
        {
            "territory_id": str(entry["territory_id"]),
            "name": entry["territory_name"],
            "leads_created": entry["leads_created"],
            "leads_contacted": entry["leads_contacted"],
            "leads_won": entry["leads_won"],
            "conversion_rate": entry["conversion_rate"],
            "avg_score": entry["avg_score"],
        }
        for entry in performance
    ]

    # Available cities (not yet covered by any active territory)
    available = get_uncovered_cities(db, limit=30)
    available_cities = [entry["city"] for entry in available]

    # Current crawler categories
    current_categories = list(DEFAULT_CATEGORIES) if DEFAULT_CATEGORIES else []

    # Pipeline activity (last 24 hours)
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    recent_stmt = select(PipelineRun).where(PipelineRun.started_at >= cutoff)
    recent = list(db.execute(recent_stmt).scalars().all())
    pipeline_activity = {
        "runs_24h": len(recent),
        "succeeded": sum(1 for r in recent if r.status == "succeeded"),
        "failed": sum(1 for r in recent if r.status == "failed"),
    }

    return {
        "saturated_territories": saturated_summary,
        "territory_performance": performance_summary,
        "available_cities": available_cities,
        "current_categories": current_categories,
        "pipeline_activity": pipeline_activity,
    }


def execute_growth_decision(db: Session, decision: GrowthDecision) -> dict:
    """Apply the agent's decision to the system.

    Supported decisions today:
    - `expand`: append new_cities to the specified territory's city list
    - `niche`: store new_categories as the territory's preferred_categories
      (noop for now — category filter integration is future work)
    - `source`: log-only (no alternative sources exist yet)

    Returns a result dict recording what was applied.
    """
    action = decision.action
    result: dict = {"applied": False, "decision_type": decision.decision}

    if decision.decision == "expand":
        if not action.territory_id or not action.new_cities:
            result["reason"] = "missing_territory_id_or_cities"
            return result
        try:
            territory = db.get(Territory, action.territory_id)
        except Exception:
            territory = None
        if territory is None:
            result["reason"] = "territory_not_found"
            return result

        existing = set(territory.cities or [])
        to_add = [c for c in action.new_cities if c not in existing]
        if not to_add:
            result["reason"] = "no_new_cities_to_add"
            return result

        territory.cities = list(existing | set(to_add))
        # Clear saturation so the next crawl tries the new cities.
        territory.is_saturated = False
        db.flush()
        result.update(
            {
                "applied": True,
                "territory_id": str(territory.id),
                "cities_added": to_add,
                "total_cities": len(territory.cities),
            }
        )
        return result

    if decision.decision == "niche":
        result["reason"] = "niche_shift_logged_no_action_yet"
        result["new_categories"] = action.new_categories
        return result

    if decision.decision == "source":
        result["reason"] = "source_diversification_not_implemented"
        result["new_source"] = action.new_source
        return result

    result["reason"] = f"unknown_decision_type:{decision.decision}"
    return result


def run_growth_cycle(db: Session) -> dict:
    """Full cycle: collect state, invoke agent, execute decision, log it.

    Intended to be called from a Celery task or operator API endpoint. Always
    writes a `GrowthDecisionLog` record so the history is auditable.
    """
    state = get_growth_state(db)

    # Skip if nothing to act on.
    if not state["saturated_territories"] and state["pipeline_activity"]["runs_24h"] > 0:
        logger.info("growth_cycle_skipped_no_trigger")
        return {"status": "skipped", "reason": "no_trigger_conditions"}

    decision = decide_growth_strategy(state)
    result = execute_growth_decision(db, decision)

    log_entry = GrowthDecisionLog(
        decision_type=decision.decision,
        reason=decision.reason,
        action_data=decision.action.model_dump(),
        confidence=decision.confidence,
        result=result,
    )
    db.add(log_entry)
    db.flush()

    logger.info(
        "growth_cycle_completed",
        decision=decision.decision,
        applied=result.get("applied", False),
        confidence=decision.confidence,
    )

    return {
        "status": "ok",
        "decision": decision.model_dump(),
        "result": result,
    }
