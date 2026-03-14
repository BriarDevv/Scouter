"""Mail credentials service — singleton CRUD + effective config resolution."""

from __future__ import annotations

import imaplib
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings as env
from app.core.logging import get_logger
from app.models.mail_credentials import MailCredentials

logger = get_logger(__name__)
_SINGLETON_ID = 1
_TEST_TIMEOUT = 10


# ── Singleton CRUD ────────────────────────────────────────────────────


def _friendly_conn_error(exc: Exception) -> str:
    """Convert raw connection errors to user-friendly Spanish messages."""
    msg = str(exc)
    low = msg.lower()
    if "name or service not known" in low or "nodename nor servname" in low or "getaddrinfo" in low:
        return "No se pudo resolver el servidor. Verificá que el host sea correcto."
    if "connection refused" in low:
        return "Conexión rechazada. Verificá el puerto y que el servidor esté activo."
    if "timed out" in low or "etimedout" in low:
        return "Tiempo de espera agotado. El servidor no respondió en 10 segundos."
    if "ssl" in low or "certificate" in low:
        return f"Error SSL/TLS: {msg}"
    return msg


def get_or_create(db: Session) -> MailCredentials:
    row = db.get(MailCredentials, _SINGLETON_ID)
    if row is None:
        row = MailCredentials(id=_SINGLETON_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info("mail_credentials_created")
    return row


def update_credentials(db: Session, updates: dict) -> MailCredentials:
    row = get_or_create(db)
    for key, value in updates.items():
        if hasattr(row, key):
            setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    logger.info("mail_credentials_updated", fields=[k for k in updates if "password" not in k])
    return row


def to_response_dict(row: MailCredentials) -> dict:
    """Serialize for API — passwords NEVER included."""
    return {
        "smtp_host": row.smtp_host,
        "smtp_port": row.smtp_port,
        "smtp_username": row.smtp_username,
        "smtp_password_set": bool(row.smtp_password),
        "smtp_ssl": row.smtp_ssl,
        "smtp_starttls": row.smtp_starttls,
        "imap_host": row.imap_host,
        "imap_port": row.imap_port,
        "imap_username": row.imap_username,
        "imap_password_set": bool(row.imap_password),
        "imap_ssl": row.imap_ssl,
        "smtp_last_test_at": row.smtp_last_test_at.isoformat() if row.smtp_last_test_at else None,
        "smtp_last_test_ok": row.smtp_last_test_ok,
        "smtp_last_test_error": row.smtp_last_test_error,
        "imap_last_test_at": row.imap_last_test_at.isoformat() if row.imap_last_test_at else None,
        "imap_last_test_ok": row.imap_last_test_ok,
        "imap_last_test_error": row.imap_last_test_error,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# ── Effective config helpers ──────────────────────────────────────────
# DB value wins over env fallback when set.

@dataclass
class EffectiveSMTPConfig:
    host: str | None
    port: int
    username: str | None
    password: str | None
    ssl: bool
    starttls: bool

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)


@dataclass
class EffectiveIMAPConfig:
    host: str | None
    port: int
    username: str | None
    password: str | None
    ssl: bool

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)


def get_effective_smtp(db: Session) -> EffectiveSMTPConfig:
    row = get_or_create(db)
    return EffectiveSMTPConfig(
        host=row.smtp_host or env.MAIL_SMTP_HOST,
        port=row.smtp_port if row.smtp_host else env.MAIL_SMTP_PORT,
        username=row.smtp_username or env.MAIL_SMTP_USERNAME,
        password=row.smtp_password or env.MAIL_SMTP_PASSWORD,
        ssl=row.smtp_ssl if row.smtp_host else env.MAIL_SMTP_SSL,
        starttls=row.smtp_starttls if row.smtp_host else env.MAIL_SMTP_STARTTLS,
    )


def get_effective_imap(db: Session) -> EffectiveIMAPConfig:
    row = get_or_create(db)
    return EffectiveIMAPConfig(
        host=row.imap_host or env.MAIL_IMAP_HOST,
        port=row.imap_port if row.imap_host else env.MAIL_IMAP_PORT,
        username=row.imap_username or env.MAIL_IMAP_USERNAME,
        password=row.imap_password or env.MAIL_IMAP_PASSWORD,
        ssl=row.imap_ssl if row.imap_host else env.MAIL_IMAP_SSL,
    )


# ── Connection tests ──────────────────────────────────────────────────

def test_smtp(db: Session) -> dict:
    """Test SMTP connectivity. Persists result. Returns {ok, error}."""
    cfg = get_effective_smtp(db)
    ok = False
    error: str | None = None
    if not cfg.host:
        error = "SMTP host no configurado."
    else:
        try:
            if cfg.ssl:
                conn = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=_TEST_TIMEOUT)
            else:
                conn = smtplib.SMTP(cfg.host, cfg.port, timeout=_TEST_TIMEOUT)
                conn.ehlo()
                if cfg.starttls:
                    conn.starttls()
                    conn.ehlo()
            if cfg.username and cfg.password:
                conn.login(cfg.username, cfg.password)
            conn.quit()
            ok = True
        except (OSError, smtplib.SMTPException) as exc:
            error = _friendly_conn_error(exc)

    row = get_or_create(db)
    row.smtp_last_test_at = datetime.now(timezone.utc)
    row.smtp_last_test_ok = ok
    row.smtp_last_test_error = error
    db.commit()
    logger.info("smtp_test", ok=ok, error=error)
    return {"ok": ok, "error": error}


def test_imap(db: Session) -> dict:
    """Test IMAP connectivity. Persists result. Returns {ok, error, sample_count}."""
    cfg = get_effective_imap(db)
    ok = False
    error: str | None = None
    sample_count: int | None = None

    if not cfg.host:
        error = "IMAP host no configurado."
    elif not cfg.username or not cfg.password:
        error = "IMAP username o password no configurado."
    else:
        try:
            if cfg.ssl:
                conn = imaplib.IMAP4_SSL(cfg.host, cfg.port, timeout=_TEST_TIMEOUT)
            else:
                conn = imaplib.IMAP4(cfg.host, cfg.port, timeout=_TEST_TIMEOUT)
            conn.login(cfg.username, cfg.password)
            status, data = conn.select("INBOX", readonly=True)
            if status == "OK":
                ok = True
                try:
                    sample_count = int(data[0]) if data and data[0] else 0
                except (ValueError, TypeError):
                    sample_count = 0
            else:
                error = f"No se pudo seleccionar INBOX: {status}"
            conn.logout()
        except (OSError, imaplib.IMAP4.error) as exc:
            error = _friendly_conn_error(exc)

    row = get_or_create(db)
    row.imap_last_test_at = datetime.now(timezone.utc)
    row.imap_last_test_ok = ok
    row.imap_last_test_error = error
    db.commit()
    logger.info("imap_test", ok=ok, error=error)
    return {"ok": ok, "error": error, "sample_count": sample_count}
