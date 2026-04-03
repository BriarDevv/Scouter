"""Read-only helpers for deploy-managed configuration.

These values are intentionally sourced from immutable deploy-time config
and must not be mutated through product runtime APIs.
"""

from __future__ import annotations

from app.core.config import settings


def get_google_maps_api_key_status() -> dict[str, object]:
    key = settings.GOOGLE_MAPS_API_KEY
    return {
        "configured": bool(key),
        "masked": f"...{key[-4:]}" if key and len(key) > 4 else None,
        "managed_by": "env",
        "mutable_via_api": False,
        "instructions": (
            "Definí GOOGLE_MAPS_API_KEY en el entorno de despliegue y reiniciá la API/worker."
        ),
    }
