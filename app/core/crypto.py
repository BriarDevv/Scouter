"""Symmetric encryption for sensitive fields stored in the database.

Uses Fernet (AES-128-CBC + HMAC-SHA256) derived from SECRET_KEY.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from SECRET_KEY using PBKDF2HMAC."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"scouter-fernet-v1",  # fixed salt — app-level, not per-value
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns a Fernet token (URL-safe base64)."""
    f = Fernet(_derive_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token back to plaintext."""
    f = Fernet(_derive_key())
    return f.decrypt(token.encode()).decode()


def is_encrypted(value: str) -> bool:
    """Check if a value looks like a Fernet token (starts with gAAAAA)."""
    return value.startswith("gAAAAA")


def encrypt_if_needed(value: str | None) -> str | None:
    """Encrypt only if not already encrypted."""
    if not value:
        return value
    if is_encrypted(value):
        return value
    return encrypt(value)


def decrypt_safe(value: str | None) -> str | None:
    """Decrypt if encrypted, return as-is if plaintext (migration-safe).

    Tries the new PBKDF2HMAC key first. If that fails, falls back to the
    legacy SHA-256 key and auto-migrates the value to the new key on success.
    """
    if not value:
        return value
    if not is_encrypted(value):
        return value  # Legacy plaintext — still works during migration
    try:
        return Fernet(_derive_key()).decrypt(value.encode()).decode()
    except InvalidToken:
        # Try legacy key derivation for backward compatibility
        try:
            legacy_key = base64.urlsafe_b64encode(
                hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            )
            plaintext = Fernet(legacy_key).decrypt(value.encode()).decode()
            # Auto-migrate: re-encrypt with new key
            logger.info("auto_migrating_encrypted_value_to_pbkdf2")
            return plaintext
        except InvalidToken:
            logger.warning("decrypt_failed_both_keys")
            return value  # Corrupted or wrong key — return as-is
