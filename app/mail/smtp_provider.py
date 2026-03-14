from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.mail.provider import MailProviderError, MailSendRequest, MailSendResult


class SMTPMailProvider:
    name = "smtp"

    def send_email(self, request: MailSendRequest) -> MailSendResult:
        smtp_host = (request.smtp_host or "").strip()
        if not smtp_host:
            raise MailProviderError("MAIL_SMTP_HOST is not configured.")
        if not request.from_email:
            raise MailProviderError("MAIL_FROM_EMAIL is not configured.")
        smtp_port = request.smtp_port or 587
        smtp_ssl = bool(request.smtp_ssl)
        smtp_starttls = bool(request.smtp_starttls)
        if smtp_ssl and smtp_starttls:
            raise MailProviderError("MAIL_SMTP_SSL and MAIL_SMTP_STARTTLS cannot both be enabled.")
        if bool(request.smtp_username) != bool(request.smtp_password):
            raise MailProviderError(
                "MAIL_SMTP_USERNAME and MAIL_SMTP_PASSWORD must both be set for SMTP auth."
            )

        message = EmailMessage()
        message["From"] = formataddr((request.from_name, request.from_email))
        message["To"] = request.recipient_email
        message["Subject"] = request.subject
        if request.reply_to:
            message["Reply-To"] = request.reply_to
        if request.in_reply_to:
            message["In-Reply-To"] = self._wrap_message_id(request.in_reply_to)
        if request.references_raw:
            message["References"] = self._normalize_references(request.references_raw)

        message_id = make_msgid(domain=request.from_email.split("@", 1)[-1])
        message["Message-ID"] = message_id
        message.set_content(request.body)

        try:
            if smtp_ssl:
                with smtplib.SMTP_SSL(
                    smtp_host,
                    smtp_port,
                    timeout=request.timeout_seconds,
                ) as server:
                    self._login(server, request)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    smtp_host,
                    smtp_port,
                    timeout=request.timeout_seconds,
                ) as server:
                    server.ehlo()
                    if smtp_starttls:
                        server.starttls()
                        server.ehlo()
                    self._login(server, request)
                    server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailProviderError(str(exc)) from exc

        return MailSendResult(
            provider=self.name,
            provider_message_id=message_id.strip("<>"),
            recipient_email=request.recipient_email,
            sent_at=datetime.now(UTC),
        )

    @staticmethod
    def _login(server: smtplib.SMTP, request: MailSendRequest) -> None:
        if request.smtp_username and request.smtp_password:
            server.login(request.smtp_username, request.smtp_password)

    @staticmethod
    def _wrap_message_id(message_id: str) -> str:
        cleaned = message_id.strip()
        if cleaned.startswith("<") and cleaned.endswith(">"):
            return cleaned
        return f"<{cleaned}>"

    @classmethod
    def _normalize_references(cls, references_raw: str) -> str:
        parts = [part.strip() for part in references_raw.split() if part.strip()]
        return " ".join(cls._wrap_message_id(part) for part in parts)
