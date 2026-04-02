"""Tests for research reports, research service, and export service."""

import csv
import io
import json
import uuid
from unittest.mock import MagicMock, patch

from app.models.lead import Lead, LeadStatus
from app.models.research_report import (
    ConfidenceLevel,
    LeadResearchReport,
    ResearchStatus,
)


def test_create_research_report_model(db):
    """Test creating a LeadResearchReport via ORM."""
    lead = Lead(business_name="Test Biz", status=LeadStatus.NEW)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    report = LeadResearchReport(
        lead_id=lead.id,
        status=ResearchStatus.PENDING,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    assert report.id is not None
    assert report.lead_id == lead.id
    assert report.status == ResearchStatus.PENDING
    assert report.website_exists is None
    assert report.created_at is not None


def test_research_report_completed(db):
    """Test updating a research report to COMPLETED with data."""
    lead = Lead(business_name="Completed Biz", status=LeadStatus.NEW)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    report = LeadResearchReport(
        lead_id=lead.id,
        status=ResearchStatus.COMPLETED,
        website_exists=True,
        website_url_verified="https://example.com",
        website_confidence=ConfidenceLevel.CONFIRMED,
        whatsapp_detected=False,
        whatsapp_confidence=ConfidenceLevel.UNKNOWN,
        detected_signals_json=[{"type": "has_ssl", "detail": "HTTPS", "confidence": 1.0}],
        research_duration_ms=1234,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    assert report.status == ResearchStatus.COMPLETED
    assert report.website_exists is True
    assert report.website_confidence == ConfidenceLevel.CONFIRMED
    assert report.research_duration_ms == 1234
    assert len(report.detected_signals_json) == 1


def test_research_service_no_website(db):
    """Test research service for a lead without a website."""
    from app.services.research_service import run_research

    lead = Lead(
        business_name="No Web Biz",
        industry="Gastronomia",
        city="Buenos Aires",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    report = run_research(db, lead.id)

    assert report is not None
    assert report.status == ResearchStatus.COMPLETED
    assert report.website_exists is False
    assert report.website_confidence == ConfidenceLevel.CONFIRMED
    assert report.detected_signals_json is not None
    assert any(s["type"] == "no_website" for s in report.detected_signals_json)


def test_research_service_with_website_mock(db):
    """Test research service with a mocked httpx response for a website."""
    from app.services.research_service import run_research

    lead = Lead(
        business_name="Web Biz",
        industry="Retail",
        city="Cordoba",
        website_url="https://example.com",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
    <head><title>Example Biz</title>
    <meta name="description" content="A great business">
    </head>
    <body>Contact us on wa.me/123456</body>
    </html>
    """

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("httpx.Client", return_value=mock_client):
        report = run_research(db, lead.id)

    assert report is not None
    assert report.status == ResearchStatus.COMPLETED
    assert report.website_exists is True
    assert report.website_confidence == ConfidenceLevel.CONFIRMED
    assert report.whatsapp_detected is True
    assert report.whatsapp_confidence == ConfidenceLevel.PROBABLE
    assert report.html_metadata_json is not None
    assert report.html_metadata_json.get("title") == "Example Biz"


def test_research_service_lead_not_found(db):
    """Test research service returns None for nonexistent lead."""
    from app.services.research_service import run_research

    fake_id = uuid.uuid4()
    result = run_research(db, fake_id)
    assert result is None


def test_export_csv(db):
    """Test CSV export produces valid output."""
    from app.services.export_service import export_leads_csv

    lead = Lead(
        business_name="CSV Biz",
        industry="Tech",
        city="Rosario",
        email="test@example.com",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    data = export_leads_csv(db, [lead])
    text = data.decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 2  # header + 1 data row
    assert rows[0][0] == "id"
    assert rows[1][1] == "CSV Biz"


def test_export_json(db):
    """Test JSON export produces valid output."""
    from app.services.export_service import export_leads_json

    lead = Lead(
        business_name="JSON Biz",
        industry="Services",
        city="Mendoza",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    data = export_leads_json(db, [lead])
    parsed = json.loads(data.decode("utf-8"))

    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["business_name"] == "JSON Biz"
    assert parsed[0]["status"] == "new"


def test_lead_signal_confidence_source(db):
    """Test that LeadSignal supports confidence and source fields."""
    from app.models.lead_signal import LeadSignal, SignalType

    lead = Lead(business_name="Signal Biz", status=LeadStatus.NEW)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    signal = LeadSignal(
        lead_id=lead.id,
        signal_type=SignalType.NO_WEBSITE,
        detail="No website found",
        confidence=0.95,
        source="research",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    assert signal.confidence == 0.95
    assert signal.source == "research"


def test_create_or_get_report_idempotent(db):
    """Test create_or_get_report returns existing report on second call."""
    from app.services.research_service import create_or_get_report

    lead = Lead(business_name="Idempotent Biz", status=LeadStatus.NEW)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    report1 = create_or_get_report(db, lead.id)
    report2 = create_or_get_report(db, lead.id)

    assert report1.id == report2.id
