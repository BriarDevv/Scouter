#!/usr/bin/env python3
"""Preflight secret validator.

Fails loudly when required secrets are missing, the SECRET_KEY is still the
template placeholder, or the database has encrypted rows that can no longer be
decrypted because the SECRET_KEY has drifted.

Exit codes:
    0 — all required secrets present, no inconsistencies detected
    1 — one or more required secrets missing or placeholder
    2 — secrets OK but database has encrypted rows that won't decrypt

Usage:
    .venv/bin/python scripts/check_secrets.py
    make preflight-secrets
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import NamedTuple


class RequiredCheck(NamedTuple):
    var: str
    predicate: Callable[[object], bool]
    failure_reason: str


_PLACEHOLDER_MARKER = "change-me"


REQUIRED: list[RequiredCheck] = [
    RequiredCheck(
        var="SECRET_KEY",
        predicate=lambda v: bool(v) and _PLACEHOLDER_MARKER not in str(v),
        failure_reason=(
            "missing or still the .env.example placeholder 'change-me-...'. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))" '
            "and save it to your password manager."
        ),
    ),
    # NOTE: GOOGLE_MAPS_API_KEY is no longer a plain env-var check because the
    # key can now live in the integration_credentials DB row. See
    # _check_google_maps_key() below, which does a DB-first / env-fallback
    # check and is invoked from main() alongside the REQUIRED loop.
]

OPTIONAL_BUT_EXPECTED: dict[str, str] = {
    "MAIL_SMTP_HOST": "no SMTP host configured — outbound mail will be unavailable",
    "MAIL_SMTP_USERNAME": "no SMTP username — outbound mail will be unavailable",
    "MAIL_IMAP_HOST": "no IMAP host configured — inbox sync will be unavailable",
    "MAIL_IMAP_USERNAME": "no IMAP username — inbox sync will be unavailable",
}


def _check_encrypted_rows_vs_placeholder(settings) -> str | None:
    """Return an error message if DB has encrypted rows but SECRET_KEY is placeholder.

    Best-effort: if the DB is unreachable we return None and the caller only
    surfaces a soft warning. We never let a DB hiccup fail the preflight.
    """
    if _PLACEHOLDER_MARKER not in (settings.SECRET_KEY or ""):
        return None  # SECRET_KEY is real — DB decryption will presumably work.

    try:
        from app.db.session import SessionLocal
        from app.models.mail_credentials import MailCredentials
    except Exception as exc:  # pragma: no cover - import guard only
        return f"DB check skipped: could not import models ({exc})"

    try:
        with SessionLocal() as db:
            row = db.get(MailCredentials, 1)
    except Exception as exc:
        return f"DB check skipped: could not connect ({exc})"

    if row is None:
        return None

    encrypted_fields = []
    if row.smtp_password:
        encrypted_fields.append("smtp_password")
    if row.imap_password:
        encrypted_fields.append("imap_password")

    if not encrypted_fields:
        return None

    return (
        "mail_credentials row 1 contains encrypted fields "
        f"({', '.join(encrypted_fields)}) but SECRET_KEY is the template placeholder. "
        "These ciphertexts were produced with a different SECRET_KEY and will NOT "
        "decrypt. Either restore the original SECRET_KEY from a backup, or wipe the "
        "encrypted fields via the Credenciales tab in the dashboard and re-enter them."
    )


def _check_google_maps_key(settings) -> tuple[str | None, bool]:
    """Return (message, is_blocking).

    message is None when the key is confirmed available.  When the DB is
    unreachable the key *may* be stored there, so we return a non-blocking
    warning instead of a hard failure — avoids the chicken-and-egg where the
    preflight runs before Docker (and therefore PostgreSQL) is up.
    """
    env_key = settings.GOOGLE_MAPS_API_KEY or None

    try:
        from app.db.session import SessionLocal
        from app.services.deploy.deploy_config_service import get_effective_google_maps_key
    except Exception:
        # Models or service can't be imported — fall back to env-only.
        if env_key:
            return None, False
        return (
            "GOOGLE_MAPS_API_KEY not set in .env and DB check could not run. "
            "If the key is stored in the DB it will be available once the "
            "backend starts. Otherwise set it via Configuración → Crawlers.",
            False,
        )

    try:
        with SessionLocal() as db:
            effective = get_effective_google_maps_key(db)
    except Exception:
        # DB unreachable — the key may be stored there already.
        if env_key:
            return None, False
        return (
            "GOOGLE_MAPS_API_KEY not set in .env and the DB is unreachable. "
            "If the key is stored in the DB it will be available once "
            "PostgreSQL starts.",
            False,
        )

    if effective:
        return None, False

    # DB is reachable and the key is genuinely missing — block.
    return (
        "Google Maps API key is not configured. Set it via "
        "Configuración → Crawlers in the dashboard (stored encrypted in DB) "
        "or define GOOGLE_MAPS_API_KEY in .env as a fallback.",
        True,
    )


def main() -> int:
    try:
        from app.core.config import settings
    except Exception as exc:
        print(f"ERROR: failed to import app.core.config — {exc}", file=sys.stderr)
        return 1

    missing: list[str] = []
    warnings: list[str] = []

    for check in REQUIRED:
        value = getattr(settings, check.var, None)
        if not check.predicate(value):
            missing.append(f"  - {check.var}: {check.failure_reason}")

    maps_msg, maps_blocking = _check_google_maps_key(settings)
    if maps_msg and maps_blocking:
        missing.append(f"  - GOOGLE_MAPS_API_KEY: {maps_msg}")
    elif maps_msg:
        warnings.append(f"  - GOOGLE_MAPS_API_KEY: {maps_msg}")
    for var, msg in OPTIONAL_BUT_EXPECTED.items():
        if not getattr(settings, var, None):
            warnings.append(f"  - {var}: {msg}")

    db_problem = _check_encrypted_rows_vs_placeholder(settings)

    # Always print every problem we found, then decide exit code based on severity.
    if missing:
        print("MISSING REQUIRED SECRETS:")
        for line in missing:
            print(line)
        print()

    if db_problem:
        print("DB CONSISTENCY ERROR:")
        print(f"  - {db_problem}")
        print()

    if warnings:
        print("Warnings (not blocking):")
        for line in warnings:
            print(line)
        print()

    if missing:
        print(
            "Fix the required items above in .env, restart the backend, "
            "then re-run: make preflight-secrets"
        )
        return 1

    if db_problem:
        return 2

    print("\u2713 secrets look OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
