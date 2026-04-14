"""Regression tests for auto-unsaturation of long-idle territories.

Closes the gap documented in docs/audits/repo-deep-audit.md section 6:
a territory flipped to is_saturated=True after two high-dup crawls and
had no automatic recovery path. If supply later grew (new businesses),
the territory stayed dead until an operator noticed and flipped the flag.

sweep_unsaturate_old_territories() now resets is_saturated=False for any
territory whose last crawl was >60 days ago.
"""

from datetime import UTC, datetime, timedelta

from app.models.territory import Territory
from app.workers.janitor import UNSATURATE_THRESHOLD_DAYS, sweep_unsaturate_old_territories


def _make_territory(
    db,
    *,
    name: str,
    is_saturated: bool,
    last_crawled_at: datetime | None,
    last_dup_ratio: float | None = 0.95,
) -> Territory:
    territory = Territory(
        name=name,
        cities=["Test"],
        is_active=True,
        is_saturated=is_saturated,
        last_crawled_at=last_crawled_at,
        last_dup_ratio=last_dup_ratio,
    )
    db.add(territory)
    db.commit()
    db.refresh(territory)
    return territory


def test_sweep_unsaturates_territory_older_than_threshold(db):
    last_crawled = datetime.now(UTC) - timedelta(days=UNSATURATE_THRESHOLD_DAYS + 30)
    territory = _make_territory(
        db, name="Old Saturated", is_saturated=True, last_crawled_at=last_crawled
    )

    count = sweep_unsaturate_old_territories(db)
    db.commit()

    assert count == 1
    db.refresh(territory)
    assert territory.is_saturated is False
    assert territory.last_dup_ratio is None


def test_sweep_leaves_recently_crawled_saturated_territory_alone(db):
    last_crawled = datetime.now(UTC) - timedelta(days=UNSATURATE_THRESHOLD_DAYS - 30)
    territory = _make_territory(
        db, name="Recent Saturated", is_saturated=True, last_crawled_at=last_crawled
    )

    count = sweep_unsaturate_old_territories(db)
    db.commit()

    assert count == 0
    db.refresh(territory)
    assert territory.is_saturated is True
    assert territory.last_dup_ratio == 0.95


def test_sweep_skips_territory_with_null_last_crawled_at(db):
    """Never-crawled territories are NOT touched (they should not be saturated
    in the first place, and if they are, operator intent is preserved)."""
    territory = _make_territory(db, name="Never Crawled", is_saturated=True, last_crawled_at=None)

    count = sweep_unsaturate_old_territories(db)
    db.commit()

    assert count == 0
    db.refresh(territory)
    assert territory.is_saturated is True


def test_sweep_ignores_unsaturated_territories(db):
    last_crawled = datetime.now(UTC) - timedelta(days=UNSATURATE_THRESHOLD_DAYS + 30)
    territory = _make_territory(
        db, name="Already Open", is_saturated=False, last_crawled_at=last_crawled
    )

    count = sweep_unsaturate_old_territories(db)
    db.commit()

    assert count == 0
    db.refresh(territory)
    assert territory.is_saturated is False


def test_main_sweep_reports_territory_count_in_result(db):
    """sweep_stale_tasks composition must surface the unsaturated count."""
    from app.workers.janitor import sweep_stale_tasks

    last_crawled = datetime.now(UTC) - timedelta(days=UNSATURATE_THRESHOLD_DAYS + 5)
    _make_territory(db, name="Composed Sweep", is_saturated=True, last_crawled_at=last_crawled)

    result = sweep_stale_tasks(session_factory=lambda: db)

    assert result["territories_unsaturated"] == 1
