from datetime import datetime, timedelta, timezone

from app.models.lead import Lead, LeadStatus
from app.models.lead_source import LeadSource, SourceType
from app.models.outreach import DraftStatus, LogAction, OutreachDraft, OutreachLog


def seed_dashboard_data(db):
    now = datetime.now(timezone.utc)

    crawler = LeadSource(name="Crawler BA", source_type=SourceType.CRAWLER)
    manual = LeadSource(name="Manual", source_type=SourceType.MANUAL)
    db.add_all([crawler, manual])
    db.flush()

    leads = [
        Lead(
            business_name="Won Lead",
            industry="Salud",
            city="Mendoza",
            score=82,
            status=LeadStatus.WON,
            source_id=crawler.id,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=1),
        ),
        Lead(
            business_name="Reply Lead",
            industry="Salud",
            city="Mendoza",
            score=58,
            status=LeadStatus.REPLIED,
            source_id=crawler.id,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=1),
        ),
        Lead(
            business_name="Lost Lead",
            industry="Retail",
            city="Rosario",
            score=33,
            status=LeadStatus.LOST,
            source_id=manual.id,
            created_at=now - timedelta(days=7),
            updated_at=now - timedelta(days=2),
        ),
        Lead(
            business_name="Fresh Lead",
            industry="Retail",
            city="Rosario",
            score=None,
            status=LeadStatus.NEW,
            source_id=manual.id,
            created_at=now,
            updated_at=now,
        ),
        Lead(
            business_name="Suppressed Lead",
            industry="Servicios",
            city="Cordoba",
            score=41,
            status=LeadStatus.SUPPRESSED,
            source_id=manual.id,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        ),
    ]
    db.add_all(leads)
    db.flush()

    sent_draft = OutreachDraft(
        lead_id=leads[0].id,
        subject="Sent subject",
        body="Sent body",
        status=DraftStatus.SENT,
        generated_at=now - timedelta(days=2),
        reviewed_at=now - timedelta(days=2),
        sent_at=now - timedelta(days=1),
    )
    db.add(sent_draft)
    db.flush()

    db.add_all(
        [
            OutreachLog(
                lead_id=leads[1].id,
                draft_id=None,
                action=LogAction.REPLIED,
                actor="system",
                detail="Positive reply",
                created_at=now - timedelta(days=1),
            ),
            OutreachLog(
                lead_id=leads[0].id,
                draft_id=sent_draft.id,
                action=LogAction.WON,
                actor="user",
                detail="Deal closed",
                created_at=now - timedelta(days=1),
            ),
        ]
    )
    db.commit()


def test_dashboard_stats_and_pipeline(client, db):
    seed_dashboard_data(db)

    stats_resp = client.get("/api/v1/dashboard/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_leads"] == 5
    assert stats["new_today"] == 1
    assert stats["contacted"] == 3
    assert stats["replied"] == 2
    assert stats["won"] == 1
    assert stats["suppressed"] == 1
    assert stats["avg_score"] == 53.5

    pipeline_resp = client.get("/api/v1/dashboard/pipeline")
    assert pipeline_resp.status_code == 200
    pipeline = pipeline_resp.json()
    assert pipeline[0]["stage"] == "new"
    assert pipeline[0]["count"] == 4
    assert pipeline[-1]["stage"] == "won"
    assert pipeline[-1]["count"] == 1


def test_dashboard_time_series_and_performance(client, db):
    seed_dashboard_data(db)

    time_series_resp = client.get("/api/v1/dashboard/time-series?days=7")
    assert time_series_resp.status_code == 200
    series = time_series_resp.json()
    assert len(series) == 7
    assert any(point["outreach"] == 1 for point in series)
    assert any(point["replies"] == 1 for point in series)
    assert any(point["conversions"] == 1 for point in series)

    industry_resp = client.get("/api/v1/performance/industry")
    assert industry_resp.status_code == 200
    industry = industry_resp.json()
    assert industry[0]["industry"] == "Salud"

    city_resp = client.get("/api/v1/performance/city")
    assert city_resp.status_code == 200
    cities = city_resp.json()
    assert {item["city"] for item in cities} >= {"Mendoza", "Rosario"}

    source_resp = client.get("/api/v1/performance/source")
    assert source_resp.status_code == 200
    sources = source_resp.json()
    assert {item["source"] for item in sources} >= {"Crawler BA", "Manual"}

    activity_resp = client.get("/api/v1/dashboard/activity?limit=5")
    assert activity_resp.status_code == 200
    activity = activity_resp.json()
    assert len(activity) == 2


def test_dashboard_cors_allows_local_wsl_origins(client):
    localhost_preflight = client.options(
        "/api/v1/dashboard/stats",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert localhost_preflight.status_code == 200
    assert localhost_preflight.headers["access-control-allow-origin"] == "http://localhost:3000"

    loopback_preflight = client.options(
        "/api/v1/dashboard/stats",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert loopback_preflight.status_code == 200
    assert loopback_preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
