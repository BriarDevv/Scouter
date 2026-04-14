"""Territory adjacency helpers — nearby / similar city discovery.

`app/data/cities_ar.py` is a flat mapping of city name → (lat, lng) without
province information. To support Growth Agent expansion decisions we keep a
small, hand-curated `CITY_PROVINCE` map for the subset of cities we already
track. When a province is unknown we degrade gracefully to string-similarity
or pure great-circle distance.

Limitation: the province mapping only covers the cities present in
`CITY_COORDS`. Cities outside that set will not be returned by
`get_cities_in_province` — extend both dictionaries together when onboarding
new regions.
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.cities_ar import CITY_COORDS
from app.models.territory import Territory

# ---------------------------------------------------------------------------
# Province mapping
# ---------------------------------------------------------------------------
# Province names follow the official Argentinian names (no accent normalization
# — we match on exact keys from this dict only).
CITY_PROVINCE: dict[str, str] = {
    # CABA & GBA (Buenos Aires conurbation)
    "Buenos Aires": "CABA",
    "CABA": "CABA",
    "Capital Federal": "CABA",
    "Palermo": "CABA",
    "Belgrano": "CABA",
    "Recoleta": "CABA",
    "Caballito": "CABA",
    "Villa Urquiza": "CABA",
    "Flores": "CABA",
    "Barracas": "CABA",
    "Almagro": "CABA",
    "Villa Crespo": "CABA",
    "Boedo": "CABA",
    # Provincia de Buenos Aires
    "San Isidro": "Buenos Aires",
    "Tigre": "Buenos Aires",
    "Pilar": "Buenos Aires",
    "Quilmes": "Buenos Aires",
    "Lomas de Zamora": "Buenos Aires",
    "Morón": "Buenos Aires",
    "Lanús": "Buenos Aires",
    "Avellaneda": "Buenos Aires",
    "Vicente López": "Buenos Aires",
    "San Martín": "Buenos Aires",
    "San Fernando": "Buenos Aires",
    "Florencio Varela": "Buenos Aires",
    "Berazategui": "Buenos Aires",
    "Ituzaingó": "Buenos Aires",
    "Merlo": "Buenos Aires",
    "Moreno": "Buenos Aires",
    "José C. Paz": "Buenos Aires",
    "Malvinas Argentinas": "Buenos Aires",
    "Escobar": "Buenos Aires",
    "La Matanza": "Buenos Aires",
    "Ezeiza": "Buenos Aires",
    "La Plata": "Buenos Aires",
    "Mar del Plata": "Buenos Aires",
    "Bahía Blanca": "Buenos Aires",
    "Tandil": "Buenos Aires",
    "Olavarría": "Buenos Aires",
    "Junín": "Buenos Aires",
    "Pergamino": "Buenos Aires",
    "San Nicolás de los Arroyos": "Buenos Aires",
    "Zárate": "Buenos Aires",
    "Campana": "Buenos Aires",
    # Córdoba
    "Córdoba": "Córdoba",
    "Río Cuarto": "Córdoba",
    "Villa Carlos Paz": "Córdoba",
    "Villa María": "Córdoba",
    "San Francisco": "Córdoba",
    "Río Tercero": "Córdoba",
    # Santa Fe
    "Rosario": "Santa Fe",
    "Santa Fe": "Santa Fe",
    "Rafaela": "Santa Fe",
    "Venado Tuerto": "Santa Fe",
    # Mendoza
    "Mendoza": "Mendoza",
    "San Rafael": "Mendoza",
    # Tucumán
    "Tucumán": "Tucumán",
    "San Miguel de Tucumán": "Tucumán",
    # Salta / Jujuy
    "Salta": "Salta",
    "San Salvador de Jujuy": "Jujuy",
    # Other interior provinces
    "San Juan": "San Juan",
    "Resistencia": "Chaco",
    "Neuquén": "Neuquén",
    "Posadas": "Misiones",
    "San Luis": "San Luis",
    "Paraná": "Entre Ríos",
    "Concordia": "Entre Ríos",
    "Formosa": "Formosa",
    "Corrientes": "Corrientes",
    "Santiago del Estero": "Santiago del Estero",
    "La Rioja": "La Rioja",
    "Catamarca": "Catamarca",
    "San Fernando del Valle de Catamarca": "Catamarca",
    # Patagonia
    "Rawson": "Chubut",
    "Trelew": "Chubut",
    "Puerto Madryn": "Chubut",
    "Comodoro Rivadavia": "Chubut",
    "Río Gallegos": "Santa Cruz",
    "Ushuaia": "Tierra del Fuego",
    "Viedma": "Río Negro",
    "San Carlos de Bariloche": "Río Negro",
    "Santa Rosa": "La Pampa",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(value: str) -> str:
    """Lowercase and strip punctuation so names compare loosely."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance between two (lat, lng) points in kilometres."""
    lat1, lng1 = a
    lat2, lng2 = b
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _covered_cities(db: Session) -> set[str]:
    """Return the set of city names already covered by any active territory."""
    covered: set[str] = set()
    stmt = select(Territory.cities).where(Territory.is_active.is_(True))
    for (cities,) in db.execute(stmt).all():
        if not cities:
            continue
        covered.update(cities)
    return covered


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_cities_in_province(province: str, exclude: set[str] | None = None) -> list[str]:
    """Return all known cities in the given province, excluding covered ones.

    Province matching is case-insensitive. When `exclude` is provided the
    matching cities are filtered out of the result. The result is sorted
    alphabetically for deterministic output.
    """
    if not province:
        return []
    target = province.strip().lower()
    excluded = exclude or set()
    result = [
        city
        for city, prov in CITY_PROVINCE.items()
        if prov.lower() == target and city not in excluded
    ]
    return sorted(result)


def get_cities_by_similarity(reference_city: str, limit: int = 10) -> list[str]:
    """Return cities "similar" to the reference, best match first.

    Similarity is computed as a weighted blend of:
    - same province (strong signal)
    - haversine distance (closer = more similar)
    - string similarity on the name (fallback when coordinates unknown)

    The reference city itself is never included. Returns at most `limit`
    cities.
    """
    if not reference_city or limit <= 0:
        return []

    ref_province = CITY_PROVINCE.get(reference_city)
    ref_coords = CITY_COORDS.get(reference_city)

    candidates: list[tuple[str, float]] = []
    for city in CITY_COORDS:
        if city == reference_city:
            continue
        score = 0.0

        # Same province is the strongest signal.
        city_province = CITY_PROVINCE.get(city)
        if ref_province and city_province and city_province == ref_province:
            score += 1.0

        # Proximity — normalize to [0, 1] with a 1000km soft cap.
        city_coords = CITY_COORDS.get(city)
        if ref_coords and city_coords:
            distance = _haversine_km(ref_coords, city_coords)
            score += max(0.0, 1.0 - min(distance, 1000.0) / 1000.0)

        # Lexical fallback — useful when coordinates match (e.g. neighbourhoods).
        score += 0.5 * _string_similarity(reference_city, city)

        candidates.append((city, score))

    candidates.sort(key=lambda pair: pair[1], reverse=True)
    return [city for city, _ in candidates[:limit]]


def get_uncovered_cities(db: Session, limit: int = 20) -> list[dict]:
    """Return cities not present in any active Territory, with metadata.

    Each entry includes: name, province (may be None), lat, lng. Ordered by
    city name for stable output.
    """
    if limit <= 0:
        return []
    covered = _covered_cities(db)
    uncovered: list[dict] = []
    for city, coords in CITY_COORDS.items():
        if city in covered:
            continue
        lat, lng = coords
        uncovered.append(
            {
                "name": city,
                "province": CITY_PROVINCE.get(city),
                "lat": lat,
                "lng": lng,
            }
        )
    uncovered.sort(key=lambda item: item["name"])
    return uncovered[:limit]
