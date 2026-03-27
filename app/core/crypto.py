"""Symmetric encryption for sensitive fields stored in the database.

Uses Fernet (AES-128-CBC + HMAC-SHA256) derived from SECRET_KEY.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _derive_key() -> bytes:
    """Derive a 32-byte Fernet key from SECRET_KEY."""
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


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
    """Decrypt if encrypted, return as-is if plaintext (migration-safe)."""
    if not value:
        return value
    if not is_encrypted(value):
        return value  # Legacy plaintext — still works during migration
    try:
        return decrypt(value)
    except InvalidToken:
        return value  # Corrupted or wrong key — return as-is
