"""Territory auto-unsaturation sweep.

Territories flip is_saturated=True when two consecutive crawls hit
dup_ratio>0.8. The flag never clears automatically, so real-world
supply growth (new businesses, closures) is invisible until an operator
resets it. This sweep resets the flag after a configurable idle window.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.logging import get_logger

logger = get_logger(__name__)

UNSATURATE_THRESHOLD_DAYS = 60


def sweep_unsaturate_old_territories(db) -> int:
    """Reset is_saturated=False for territories not crawled in >N days.

    Skips territories with NULL last_crawled_at (never crawled): the
    saturation flag there reflects operator intent, not observed staleness.
    """
    from app.models.territory import Territory

    cutoff = datetime.now(UTC) - timedelta(days=UNSATURATE_THRESHOLD_DAYS)
    stale = (
        db.execute(
            select(Territory).where(
                Territory.is_saturated.is_(True),
                Territory.last_crawled_at.is_not(None),
                Territory.last_crawled_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    count = 0
    for territory in stale:
        days_since = (datetime.now(UTC) - territory.last_crawled_at).days
        territory.is_saturated = False
        territory.last_dup_ratio = None
        count += 1
        logger.info(
            "territory_auto_unsaturated",
            territory_id=str(territory.id),
            territory_name=territory.name,
            days_since_crawl=days_since,
        )
    return count
