"""Deploy-style config helpers.

These values (currently just `GOOGLE_MAPS_API_KEY`) used to live only in the
.env file. We now persist them in `integration_credentials` so the operator
can rotate them from the UI without a deploy. The env var remains a valid
fallback: if the DB row has no value, we read from settings. DB wins when
both are set.

This file is intentionally small. Any new integration credential belongs in
this service + `app.models.integration_credentials` to keep the boundary
clean.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_safe, encrypt_if_needed
from app.core.logging import get_logger
from app.models.integration_credentials import IntegrationCredentials

logger = get_logger(__name__)

_SINGLETON_ID = 1

# Google Maps API keys from Google Cloud Console look like `AIzaSy...`
# followed by 33 URL-safe chars. We do a soft prefix check and a loose length
# range so typos or accidental pastes get rejected without being too strict
# on future key formats.
_GOOGLE_MAPS_KEY_PREFIX = "AIza"
_GOOGLE_MAPS_KEY_MIN_LEN = 30
_GOOGLE_MAPS_KEY_MAX_LEN = 100

_KAPSO_KEY_MIN_LEN = 10
_KAPSO_KEY_MAX_LEN = 500


def _get_or_create(db: Session) -> IntegrationCredentials:
    row = db.get(IntegrationCredentials, _SINGLETON_ID)
    if row is None:
        row = IntegrationCredentials(id=_SINGLETON_ID)
        db.add(row)
        db.flush()
        db.refresh(row)
        logger.info("integration_credentials_created")
    return row


def get_effective_google_maps_key(db: Session) -> str | None:
    """Return the Google Maps API key that the crawler should actually use.

    DB value wins if present; falls back to settings.GOOGLE_MAPS_API_KEY.
    Returns None when neither is set.
    """
    row = _get_or_create(db)
    if row.google_maps_api_key:
        decrypted = decrypt_safe(row.google_maps_api_key)
        if decrypted:
            return decrypted
    return settings.GOOGLE_MAPS_API_KEY or None


def get_google_maps_api_key_status(db: Session) -> dict[str, object]:
    """Return the state of the Google Maps API key for the settings UI.

    Never exposes the raw key — only a `configured` flag, the masked tail,
    and the source (`db` or `env`) so the UI can show where the active
    value comes from.
    """
    row = _get_or_create(db)
    db_key = decrypt_safe(row.google_maps_api_key) if row.google_maps_api_key else None
    env_key = settings.GOOGLE_MAPS_API_KEY or None

    if db_key:
        source = "db"
        active = db_key
    elif env_key:
        source = "env"
        active = env_key
    else:
        source = None
        active = None

    return {
        "configured": bool(active),
        "masked": f"...{active[-4:]}" if active and len(active) > 4 else None,
        "managed_by": source or "none",
        "source": source,
        "mutable_via_api": True,
        "updated_at": (
            row.google_maps_api_key_updated_at.isoformat()
            if row.google_maps_api_key_updated_at
            else None
        ),
        "instructions": (
            "Cargá la key directamente desde este panel (se guarda encriptada en la DB) "
            "o dejá GOOGLE_MAPS_API_KEY en el .env como fallback. El valor de la DB "
            "tiene prioridad cuando ambos están definidos."
        ),
    }


class InvalidGoogleMapsKeyError(ValueError):
    """Raised when a proposed Google Maps API key fails format validation."""


def _validate_google_maps_key(key: str) -> str:
    stripped = key.strip()
    if not stripped:
        raise InvalidGoogleMapsKeyError("API key vacía")
    if len(stripped) < _GOOGLE_MAPS_KEY_MIN_LEN or len(stripped) > _GOOGLE_MAPS_KEY_MAX_LEN:
        raise InvalidGoogleMapsKeyError(
            f"Longitud fuera de rango ({_GOOGLE_MAPS_KEY_MIN_LEN}-{_GOOGLE_MAPS_KEY_MAX_LEN})"
        )
    if not stripped.startswith(_GOOGLE_MAPS_KEY_PREFIX):
        raise InvalidGoogleMapsKeyError(
            f"Las keys de Google Maps empiezan con '{_GOOGLE_MAPS_KEY_PREFIX}'"
        )
    return stripped


def set_google_maps_api_key(db: Session, key: str) -> dict[str, object]:
    """Persist an encrypted Google Maps API key in integration_credentials."""
    validated = _validate_google_maps_key(key)
    row = _get_or_create(db)
    row.google_maps_api_key = encrypt_if_needed(validated)
    row.google_maps_api_key_updated_at = datetime.now(UTC)
    db.flush()
    db.refresh(row)
    logger.info("google_maps_api_key_updated", source="db")
    return get_google_maps_api_key_status(db)


def clear_google_maps_api_key(db: Session) -> dict[str, object]:
    """Wipe the DB-stored Google Maps API key (env fallback still applies)."""
    row = _get_or_create(db)
    row.google_maps_api_key = None
    row.google_maps_api_key_updated_at = datetime.now(UTC)
    db.flush()
    db.refresh(row)
    logger.info("google_maps_api_key_cleared")
    return get_google_maps_api_key_status(db)


# ── Kapso API key ─────────────────────────────────────────────────────


def get_effective_kapso_api_key(db: Session) -> str | None:
    """Return the Kapso API key the system should use. DB wins over env."""
    row = _get_or_create(db)
    if row.kapso_api_key:
        decrypted = decrypt_safe(row.kapso_api_key)
        if decrypted:
            return decrypted
    return settings.KAPSO_API_KEY or None


def get_kapso_api_key_status(db: Session) -> dict[str, object]:
    """Return the state of the Kapso API key for the settings UI."""
    row = _get_or_create(db)
    db_key = decrypt_safe(row.kapso_api_key) if row.kapso_api_key else None
    env_key = settings.KAPSO_API_KEY or None

    if db_key:
        source = "db"
        active = db_key
    elif env_key:
        source = "env"
        active = env_key
    else:
        source = None
        active = None

    return {
        "configured": bool(active),
        "masked": f"...{active[-4:]}" if active and len(active) > 4 else None,
        "source": source,
        "updated_at": (
            row.kapso_api_key_updated_at.isoformat() if row.kapso_api_key_updated_at else None
        ),
    }


class InvalidKapsoKeyError(ValueError):
    """Raised when a proposed Kapso API key fails format validation."""


def set_kapso_api_key(db: Session, key: str) -> dict[str, object]:
    """Persist an encrypted Kapso API key in integration_credentials."""
    stripped = key.strip()
    if not stripped:
        raise InvalidKapsoKeyError("API key vacía")
    if len(stripped) < _KAPSO_KEY_MIN_LEN or len(stripped) > _KAPSO_KEY_MAX_LEN:
        raise InvalidKapsoKeyError(
            f"Longitud fuera de rango ({_KAPSO_KEY_MIN_LEN}-{_KAPSO_KEY_MAX_LEN})"
        )
    row = _get_or_create(db)
    row.kapso_api_key = encrypt_if_needed(stripped)
    row.kapso_api_key_updated_at = datetime.now(UTC)
    db.flush()
    db.refresh(row)
    logger.info("kapso_api_key_updated", source="db")
    return get_kapso_api_key_status(db)
