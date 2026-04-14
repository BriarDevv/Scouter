"""Regression tests for the auto-replenish hook in task_auto_process_new_leads.

Closes the gap documented in docs/audits/repo-deep-audit.md section 3:
the beat task used to idle when no NEW leads were left, so the pipeline
would sleep until the next Mon/Thu 8am scheduled crawl. Now, if
auto_replenish_enabled is set and a non-saturated active territory exists,
the tick dispatches a crawl for the oldest-crawled territory.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models.settings import OperationalSettings
from app.models.territory import Territory


def _enable_auto_pipeline(db, *, auto_replenish: bool = True) -> None:
    ops = db.get(OperationalSettings, 1)
    if ops is None:
        ops = OperationalSettings(id=1)
        db.add(ops)
    ops.auto_pipeline_enabled = True
    ops.auto_replenish_enabled = auto_replenish
    db.commit()


def _patch_queue_depths(stub=None):
    """Patch metrics to report a healthy queue so backpressure does not trip."""
    return patch(
        "app.workers.metrics.get_queue_depths",
        return_value=stub or {"active": 0, "reserved": 0},
    )


def test_auto_replenish_dispatches_crawl_when_no_leads_and_territory_available(db):
    _enable_auto_pipeline(db, auto_replenish=True)
    territory = Territory(
        name="Quilmes",
        cities=["Quilmes"],
        is_active=True,
        is_saturated=False,
        last_crawled_at=datetime.now(UTC) - timedelta(days=5),
    )
    db.add(territory)
    db.commit()
    db.refresh(territory)

    with (
        _patch_queue_depths(),
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl_delay,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    assert result["status"] == "replenish_triggered"
    assert result["territory_id"] == str(territory.id)
    mock_crawl_delay.assert_called_once_with(str(territory.id))


def test_auto_replenish_picks_least_recently_crawled_territory(db):
    _enable_auto_pipeline(db, auto_replenish=True)

    recent = Territory(
        name="Recent",
        cities=["R"],
        is_active=True,
        last_crawled_at=datetime.now(UTC) - timedelta(hours=1),
    )
    stale = Territory(
        name="Stale",
        cities=["S"],
        is_active=True,
        last_crawled_at=datetime.now(UTC) - timedelta(days=30),
    )
    never = Territory(
        name="Never",
        cities=["N"],
        is_active=True,
        last_crawled_at=None,
    )
    db.add_all([recent, stale, never])
    db.commit()
    db.refresh(never)

    with (
        _patch_queue_depths(),
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl_delay,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    # Never-crawled territory should win (NULLS FIRST on last_crawled_at).
    assert result["territory_id"] == str(never.id)
    mock_crawl_delay.assert_called_once_with(str(never.id))


def test_auto_replenish_skipped_when_flag_disabled(db):
    _enable_auto_pipeline(db, auto_replenish=False)
    territory = Territory(name="Disabled", cities=["D"], is_active=True)
    db.add(territory)
    db.commit()

    with (
        _patch_queue_depths(),
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl_delay,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    assert result == {"status": "ok", "dispatched": 0}
    mock_crawl_delay.assert_not_called()


def test_auto_replenish_skipped_when_all_territories_saturated(db):
    _enable_auto_pipeline(db, auto_replenish=True)
    db.add(Territory(name="Sat A", cities=["A"], is_active=True, is_saturated=True))
    db.add(Territory(name="Sat B", cities=["B"], is_active=True, is_saturated=True))
    db.commit()

    with (
        _patch_queue_depths(),
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl_delay,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    assert result == {"status": "ok", "dispatched": 0}
    mock_crawl_delay.assert_not_called()


def test_auto_replenish_skipped_when_inactive_territories(db):
    _enable_auto_pipeline(db, auto_replenish=True)
    db.add(Territory(name="Off", cities=["O"], is_active=False))
    db.commit()

    with (
        _patch_queue_depths(),
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl_delay,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    assert result == {"status": "ok", "dispatched": 0}
    mock_crawl_delay.assert_not_called()


def test_auto_replenish_respects_backpressure_guard(db):
    """Auto-replenish must not fire when the queue-depth guard trips first."""
    _enable_auto_pipeline(db, auto_replenish=True)
    db.add(
        Territory(
            name="Ready",
            cities=["R"],
            is_active=True,
            is_saturated=False,
            last_crawled_at=None,
        )
    )
    db.commit()

    with (
        _patch_queue_depths({"active": 40, "reserved": 20}),
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl_delay,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    assert result["status"] == "skipped"
    assert result["reason"] == "backpressure"
    mock_crawl_delay.assert_not_called()


def test_auto_replenish_not_triggered_when_leads_exist(db):
    """If eligible NEW leads exist, behavior is unchanged (dispatch pipeline, no crawl)."""
    from app.models.lead import Lead

    _enable_auto_pipeline(db, auto_replenish=True)
    db.add(Territory(name="Ready2", cities=["R"], is_active=True, is_saturated=False))
    old_lead = Lead(
        id=uuid.uuid4(),
        business_name="Ready Biz",
        city="R",
        status="new",
    )
    db.add(old_lead)
    db.commit()
    # Back-date created_at past the _MIN_AGE_MINUTES cutoff so it is eligible.
    old_lead.created_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()

    with (
        _patch_queue_depths(),
        patch("app.workers.pipeline_tasks.task_full_pipeline.delay") as mock_full,
        patch("app.workers.crawl_tasks.task_crawl_territory.delay") as mock_crawl,
    ):
        from app.workers.auto_pipeline_tasks import task_auto_process_new_leads

        result = task_auto_process_new_leads()

    assert result["status"] == "ok"
    assert result["dispatched"] == 1
    mock_full.assert_called_once_with(str(old_lead.id))
    mock_crawl.assert_not_called()
