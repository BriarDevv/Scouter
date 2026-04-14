"""Country-code → address markers for the Google Places post-filter.

The crawler drops places whose `formattedAddress` does not contain at
least one marker. Adding a country here makes territories with the
corresponding country_code eligible. ISO 3166-1 alpha-2 codes throughout.
"""

from __future__ import annotations

from typing import Final

_COUNTRY_MARKERS: Final[dict[str, tuple[str, ...]]] = {
    "AR": ("argentina",),
    "US": ("usa", "united states"),
    "MX": ("mexico", "méxico"),
    "BR": ("brasil", "brazil"),
    "CL": ("chile",),
    "UY": ("uruguay",),
    "CO": ("colombia",),
    "ES": ("españa", "spain"),
}

_DEFAULT_MARKERS: Final[tuple[str, ...]] = _COUNTRY_MARKERS["AR"]


def markers_for_country(country_code: str | None) -> tuple[str, ...]:
    """Return the address markers for a country, or the default (AR) tuple."""
    if not country_code:
        return _DEFAULT_MARKERS
    return _COUNTRY_MARKERS.get(country_code.upper(), _DEFAULT_MARKERS)
