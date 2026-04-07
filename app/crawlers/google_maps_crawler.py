"""Google Maps Places API (New) crawler.

Searches for businesses by city + category using the Places API,
then fetches details to determine if they have a website.
Businesses without a website are high-value leads.
"""

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.crawlers.base_crawler import BaseCrawler, RawLead

logger = get_logger(__name__)

# Categories relevant for web development services — ordered by prospect value
DEFAULT_CATEGORIES = [
    # High-value: service businesses that benefit most from a website
    "restaurante",
    "clinica",
    "consultorio odontologico",
    "inmobiliaria",
    "hotel",
    "hostel",
    "estudio contable",
    "abogado",
    "estudio juridico",
    # Medium-high: personal care, fitness, retail
    "peluqueria",
    "barberia",
    "gimnasio",
    "veterinaria",
    "optica",
    "boutique",
    # Medium: food/hospitality
    "cafeteria",
    "bar",
    "panaderia",
    "floreria",
    "ferreteria",
    "libreria",
]

_PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.shortFormattedAddress",
        "places.addressComponents",
        "places.nationalPhoneNumber",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.types",
        "places.primaryType",
        "places.primaryTypeDisplayName",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "places.regularOpeningHours",
        "places.location",
    ]
)


class GoogleMapsCrawler(BaseCrawler):
    """Crawl Google Maps for businesses in a given city/zone + category."""

    @property
    def source_name(self) -> str:
        return "google_maps"

    def crawl(
        self,
        city: str,
        zone: str | None = None,
        categories: list[str] | None = None,
        max_results_per_category: int = 20,
        only_without_website: bool = False,
        api_key: str | None = None,
        target_leads: int = 50,
    ) -> list[RawLead]:
        key = api_key or settings.GOOGLE_MAPS_API_KEY
        if not key:
            logger.error("google_maps_no_api_key")
            return []

        cats = categories or DEFAULT_CATEGORIES
        location = f"{zone}, {city}" if zone else city
        all_leads: list[RawLead] = []
        seen_ids: set[str] = set()

        for cat in cats:
            query = f"{cat} en {location}"
            logger.info("google_maps_search", query=query)

            try:
                results = self._search_text(key, query, max_results_per_category)
            except Exception as exc:
                logger.error("google_maps_search_error", query=query, error=str(exc))
                continue

            for place in results:
                place_id = place.get("id", "")
                if place_id in seen_ids:
                    continue
                seen_ids.add(place_id)

                display_name = place.get("displayName", {})
                name = display_name.get("text", "").strip()
                if not name:
                    continue

                raw_website = place.get("websiteUri")

                # Detect Instagram links set as website
                website = raw_website
                instagram_url = None
                if raw_website and "instagram.com" in raw_website.lower():
                    instagram_url = raw_website
                    website = None

                if only_without_website and website:
                    continue

                # Determine industry from primaryType or query category
                primary_type = place.get("primaryTypeDisplayName", {})
                industry = primary_type.get("text") or cat

                # Opening hours as comma-separated weekday text
                hours_obj = place.get("regularOpeningHours", {})
                weekday_descriptions = hours_obj.get("weekdayDescriptions", [])
                opening_hours = " | ".join(weekday_descriptions) if weekday_descriptions else None

                # Location coordinates
                location = place.get("location", {})

                lead = RawLead(
                    business_name=name,
                    industry=industry,
                    city=city,
                    zone=zone,
                    website_url=website,
                    instagram_url=instagram_url,
                    phone=place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber"),
                    source_url=place.get("googleMapsUri"),
                    address=place.get("formattedAddress") or place.get("shortFormattedAddress"),
                    google_maps_url=place.get("googleMapsUri"),
                    rating=place.get("rating"),
                    review_count=place.get("userRatingCount"),
                    business_status=place.get("businessStatus"),
                    opening_hours=opening_hours,
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                )

                all_leads.append(lead)

                # Stop early if we reached the target
                if target_leads and len(all_leads) >= target_leads:
                    logger.info(
                        "google_maps_target_reached",
                        city=city,
                        target=target_leads,
                        collected=len(all_leads),
                        category=cat,
                    )
                    break

            # Stop iterating categories if target reached
            if target_leads and len(all_leads) >= target_leads:
                break

            self._throttle()

        logger.info(
            "google_maps_crawl_done",
            city=city,
            zone=zone,
            total_leads=len(all_leads),
            categories_searched=len(cats),
        )
        return all_leads

    def _search_text(self, api_key: str, query: str, max_results: int) -> list[dict]:
        """Call Places API (New) Text Search."""
        body = {
            "textQuery": query,
            "languageCode": "es",
            "maxResultCount": min(max_results, 20),  # API max is 20
        }

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                _PLACES_SEARCH_URL,
                json=body,
                headers={
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": _FIELD_MASK,
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            error_data = (
                resp.json()
                if resp.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            error_msg = error_data.get("error", {}).get("message", resp.text[:200])
            raise RuntimeError(f"Places API error ({resp.status_code}): {error_msg}")

        data = resp.json()
        return data.get("places", [])
