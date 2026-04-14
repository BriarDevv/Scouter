"""Regression tests for Territory geo parameterization (Item 6 post-hardening).

Covers:
- Territory.country_code default 'AR' + new nullable geo fields
- geo_markers.markers_for_country mapping
- Crawler body variations (locationRestriction.rectangle, locationBias.circle,
  region-only) depending on territory shape
- country_markers plumbing from territory_crawl → crawler filter
"""

from unittest.mock import patch

from app.crawlers.google_maps_crawler import GoogleMapsCrawler
from app.models.territory import Territory
from app.services.territories.geo_markers import markers_for_country


def test_markers_for_country_known_codes():
    assert markers_for_country("AR") == ("argentina",)
    assert markers_for_country("US") == ("usa", "united states")
    assert markers_for_country("MX") == ("mexico", "méxico")


def test_markers_for_country_unknown_falls_back_to_ar():
    assert markers_for_country("ZZ") == ("argentina",)
    assert markers_for_country(None) == ("argentina",)
    assert markers_for_country("") == ("argentina",)


def test_territory_model_defaults_country_code_to_ar(db):
    t = Territory(name="Default Country", cities=["Test"])
    db.add(t)
    db.commit()
    db.refresh(t)
    assert t.country_code == "AR"
    assert t.center_lat is None
    assert t.center_lng is None
    assert t.bbox is None


def _capture_request_body() -> tuple[list[dict], type]:
    """Build a fake httpx.Client that records request bodies sent to Places API."""
    captured: list[dict] = []

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        @staticmethod
        def json():
            return {"places": []}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json, headers):
            captured.append(json)
            return FakeResponse()

    return captured, FakeClient


def test_crawler_uses_location_restriction_rectangle_when_bbox_present():
    """bbox takes precedence over territory_center and city coords."""
    captured, fake_client = _capture_request_body()
    crawler = GoogleMapsCrawler()
    bbox = {
        "sw": {"lat": -34.70, "lng": -58.55},
        "ne": {"lat": -34.53, "lng": -58.33},
    }
    with patch("app.crawlers.google_maps_crawler.httpx.Client", fake_client):
        crawler.crawl(
            city="CABA",
            categories=["restaurante"],
            max_results_per_category=5,
            api_key="k",
            target_leads=5,
            country_code="AR",
            territory_center=(-34.6037, -58.3816),
            bbox=bbox,
        )

    assert captured, "at least one Places API call expected"
    body = captured[0]
    assert body["regionCode"] == "AR"
    assert "locationRestriction" in body
    rect = body["locationRestriction"]["rectangle"]
    assert rect["low"] == {"latitude": -34.70, "longitude": -58.55}
    assert rect["high"] == {"latitude": -34.53, "longitude": -58.33}
    # When bbox is set, locationBias must NOT also be sent (precedence rule).
    assert "locationBias" not in body


def test_crawler_uses_territory_center_over_city_coords():
    """Explicit territory_center wins over city fallback when bbox absent."""
    captured, fake_client = _capture_request_body()
    crawler = GoogleMapsCrawler()
    with patch("app.crawlers.google_maps_crawler.httpx.Client", fake_client):
        crawler.crawl(
            city="CABA",  # has get_coords fallback at (-34.6037, -58.3816)
            categories=["restaurante"],
            max_results_per_category=5,
            api_key="k",
            target_leads=5,
            country_code="AR",
            territory_center=(-40.0, -70.0),  # different coords on purpose
        )

    body = captured[0]
    assert "locationRestriction" not in body
    circle = body["locationBias"]["circle"]
    assert circle["center"] == {"latitude": -40.0, "longitude": -70.0}


def test_crawler_country_filter_uses_us_markers_for_us_territory():
    """Places with 'California, USA' survive filter when country_code=US."""
    crawler = GoogleMapsCrawler()
    mixed = [
        {
            "id": "us-1",
            "displayName": {"text": "Cali Cafe"},
            "formattedAddress": "123 Main St, Los Angeles, CA, USA",
            "primaryTypeDisplayName": {"text": "cafe"},
            "googleMapsUri": "https://maps/us-1",
        },
        {
            "id": "ar-1",
            "displayName": {"text": "Cafe BA"},
            "formattedAddress": "Av. Corrientes 1234, Buenos Aires, Argentina",
            "primaryTypeDisplayName": {"text": "cafe"},
            "googleMapsUri": "https://maps/ar-1",
        },
    ]
    with patch.object(GoogleMapsCrawler, "_search_text", return_value=mixed):
        leads = crawler.crawl(
            city="Los Angeles",
            categories=["cafe"],
            max_results_per_category=5,
            api_key="k",
            target_leads=5,
            country_code="US",
            country_markers=markers_for_country("US"),
        )

    names = {lead.business_name for lead in leads}
    assert names == {"Cali Cafe"}  # AR lead dropped by US markers


def test_crawler_defaults_preserve_legacy_ar_behavior():
    """Calling crawl without the new multi-country kwargs must still target AR."""
    captured, fake_client = _capture_request_body()
    crawler = GoogleMapsCrawler()
    with patch("app.crawlers.google_maps_crawler.httpx.Client", fake_client):
        crawler.crawl(
            city="CABA",
            categories=["restaurante"],
            max_results_per_category=5,
            api_key="k",
            target_leads=5,
        )

    body = captured[0]
    assert body["regionCode"] == "AR"
    # city=CABA triggers the get_coords fallback → locationBias.circle
    assert body["locationBias"]["circle"]["center"] == {
        "latitude": -34.6037,
        "longitude": -58.3816,
    }
