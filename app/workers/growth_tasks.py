"""Growth Intelligence Celery tasks.

Runs weekly (before the AI team weekly report) to snapshot rolling-window
performance metrics for every active territory. The Growth Agent consumes
these snapshots to detect trends and drive expansion decisions.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.settings import OperationalSettings
from app.models.territory import Territory
from app.services.growth.growth_service import run_growth_cycle
from app.services.growth.performance_service import snapshot_territory_performance
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="app.workers.growth_tasks.task_snapshot_territory_performance")
def task_snapshot_territory_performance() -> dict:
    """Take performance snapshots for all active territories.

    Scheduled via Celery Beat (Sunday 21:00 Argentina time — runs before the
    weekly AI team report at 20:00 next Sunday, but scheduled an hour later
    this Sunday so the report has one fresh week of history to consume).
    """
    snapshots_created = 0
    failures = 0
    try:
        with SessionLocal() as db:
            territories = (
                db.query(Territory).filter(Territory.is_active == True).all()  # noqa: E712
            )
            if not territories:
                logger.info("growth_snapshot_no_active_territories")
                return {"status": "skipped", "reason": "no_active_territories"}

            for territory in territories:
                try:
                    snapshot_territory_performance(db, territory)
                    snapshots_created += 1
                except Exception as exc:
                    failures += 1
                    logger.warning(
                        "growth_snapshot_failed",
                        territory_id=str(territory.id),
                        territory_name=territory.name,
                        error=str(exc),
                    )
            db.commit()

        logger.info(
            "growth_snapshot_completed",
            snapshots_created=snapshots_created,
            failures=failures,
        )
        return {
            "status": "ok",
            "snapshots_created": snapshots_created,
            "failures": failures,
        }
    except Exception as exc:
        logger.error("growth_snapshot_task_failed", error=str(exc))
        return {"status": "failed", "error": str(exc)}


@celery_app.task(name="app.workers.growth_tasks.task_growth_cycle")
def task_growth_cycle() -> dict:
    """Run a Growth Intelligence decision cycle.

    Scheduled daily. The cycle only runs when:
    - `auto_pipeline_enabled` is true in operational settings, AND
    - there is at least one saturated territory OR pipeline inactivity.

    When it runs, the Growth Agent chooses between geographic expansion,
    niche shift, or source diversification, and the system applies the
    decision automatically.
    """
    try:
        with SessionLocal() as db:
            ops = db.query(OperationalSettings).first()
            if not ops or not ops.auto_pipeline_enabled:
                logger.info("growth_cycle_skipped_auto_pipeline_disabled")
                return {"status": "skipped", "reason": "auto_pipeline_disabled"}

            result = run_growth_cycle(db)
            db.commit()
            logger.info("growth_cycle_task_completed", status=result.get("status"))
            return result
    except Exception as exc:
        logger.error("growth_cycle_task_failed", error=str(exc))
        return {"status": "failed", "error": str(exc)}
