"""Tests for app.core.crypto — encrypt/decrypt round-trip and helpers."""

from app.core.crypto import decrypt, decrypt_safe, encrypt, encrypt_if_needed, is_encrypted


def test_encrypt_decrypt_roundtrip():
    plaintext = "my-super-secret-password-123!"
    token = encrypt(plaintext)
    assert token != plaintext
    assert is_encrypted(token)
    assert decrypt(token) == plaintext


def test_encrypt_if_needed_skips_already_encrypted():
    plaintext = "password123"
    token = encrypt(plaintext)
    assert encrypt_if_needed(token) == token  # should not double-encrypt


def test_encrypt_if_needed_encrypts_plaintext():
    plaintext = "password123"
    token = encrypt_if_needed(plaintext)
    assert is_encrypted(token)
    assert decrypt(token) == plaintext


def test_encrypt_if_needed_none():
    assert encrypt_if_needed(None) is None
    assert encrypt_if_needed("") is None or encrypt_if_needed("") == ""


def test_decrypt_safe_none():
    assert decrypt_safe(None) is None


def test_decrypt_safe_plaintext_passthrough():
    """Legacy plaintext values should be returned as-is."""
    assert decrypt_safe("plain-password") == "plain-password"


def test_decrypt_safe_encrypted():
    token = encrypt("secret")
    assert decrypt_safe(token) == "secret"


def test_is_encrypted():
    assert not is_encrypted("plain")
    assert not is_encrypted("")
    token = encrypt("test")
    assert is_encrypted(token)


def test_decrypt_safe_invalid_fernet_returns_none(capsys):
    """A string that looks like Fernet (starts with gAAAAA) but is invalid
    should return None (not ciphertext) and emit a warning."""
    bad_token = "gAAAAAbadtokendata1234567890abcdef"
    result = decrypt_safe(bad_token)
    assert result is None
    captured = capsys.readouterr()
    assert "decrypt" in captured.out.lower() or "decrypt" in captured.err.lower()
