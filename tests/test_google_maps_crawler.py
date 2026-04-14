"""Regression tests for Google Maps crawler geo anchoring.

Covers the CABA -> USA leak fix (audit 2026-04-13):
- regionCode="AR" must always be sent to Places API
- locationBias.circle must be set when city coords are known
- Results whose formattedAddress lacks country markers must be dropped
"""

from unittest.mock import patch

from app.crawlers.google_maps_crawler import GoogleMapsCrawler


def _fake_place(
    place_id: str,
    name: str,
    formatted_address: str,
    website: str | None = None,
) -> dict:
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": formatted_address,
        "shortFormattedAddress": formatted_address,
        "addressComponents": [],
        "websiteUri": website,
        "googleMapsUri": f"https://maps.example/{place_id}",
        "primaryTypeDisplayName": {"text": "restaurant"},
    }


def test_crawler_filters_non_argentina_results():
    """Mixed AR + US results -> only AR leads survive the country filter."""
    crawler = GoogleMapsCrawler()
    mixed = [
        _fake_place("ar-1", "Café Porteño", "Av. Corrientes 1234, Buenos Aires, Argentina"),
        _fake_place("us-1", "CABA Restaurant", "100 Main St, Los Angeles, CA, USA"),
        _fake_place("ar-2", "Parrilla San Telmo", "Defensa 500, San Telmo, CABA, Argentina"),
        _fake_place("us-2", "Cabana Bar", "200 Ocean Dr, Miami, FL, USA"),
    ]
    with patch.object(GoogleMapsCrawler, "_search_text", return_value=mixed):
        leads = crawler.crawl(
            city="CABA",
            categories=["restaurante"],
            max_results_per_category=10,
            api_key="test-key",
            target_leads=10,
        )

    names = {lead.business_name for lead in leads}
    assert names == {"Café Porteño", "Parrilla San Telmo"}
    assert all("Argentina" in (lead.address or "") for lead in leads)


def test_crawler_sends_region_code_and_location_bias():
    """Body sent to Places API must include regionCode=AR + locationBias when city coords are known."""
    captured_bodies: list[dict] = []

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
            captured_bodies.append(json)
            return FakeResponse()

    crawler = GoogleMapsCrawler()
    with patch("app.crawlers.google_maps_crawler.httpx.Client", FakeClient):
        crawler.crawl(
            city="CABA",
            categories=["restaurante"],
            max_results_per_category=5,
            api_key="test-key",
            target_leads=5,
        )

    assert captured_bodies, "crawler must POST at least one request"
    body = captured_bodies[0]
    assert body["regionCode"] == "AR"
    assert "locationBias" in body
    circle = body["locationBias"]["circle"]
    # CABA coords from app/data/cities_ar.py: (-34.6037, -58.3816)
    assert circle["center"]["latitude"] == -34.6037
    assert circle["center"]["longitude"] == -58.3816
    assert circle["radius"] == 15000


def test_crawler_omits_location_bias_for_unknown_city():
    """Unknown city -> no locationBias (still sends regionCode)."""
    captured_bodies: list[dict] = []

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
            captured_bodies.append(json)
            return FakeResponse()

    crawler = GoogleMapsCrawler()
    with patch("app.crawlers.google_maps_crawler.httpx.Client", FakeClient):
        crawler.crawl(
            city="UnknownVille",
            categories=["restaurante"],
            max_results_per_category=5,
            api_key="test-key",
            target_leads=5,
        )

    body = captured_bodies[0]
    assert body["regionCode"] == "AR"
    assert "locationBias" not in body


def test_crawler_accepts_places_without_formatted_address():
    """Places with no formattedAddress must not be dropped by the country filter.

    Edge case: some Places API responses may omit formattedAddress entirely
    when details are sparse. We should accept these instead of silently losing them.
    """
    crawler = GoogleMapsCrawler()
    places = [
        {
            "id": "no-addr-1",
            "displayName": {"text": "Sin Dirección"},
            "websiteUri": None,
            "googleMapsUri": "https://maps.example/no-addr-1",
            "primaryTypeDisplayName": {"text": "restaurant"},
        },
    ]
    with patch.object(GoogleMapsCrawler, "_search_text", return_value=places):
        leads = crawler.crawl(
            city="CABA",
            categories=["restaurante"],
            max_results_per_category=5,
            api_key="test-key",
            target_leads=5,
        )

    assert [lead.business_name for lead in leads] == ["Sin Dirección"]
