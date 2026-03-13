from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import settings
from app.mail.provider import MailProviderError, MailSendRequest, MailSendResult


class SMTPMailProvider:
    name = "smtp"

    def send_email(self, request: MailSendRequest) -> MailSendResult:
        if not settings.MAIL_SMTP_HOST:
            raise MailProviderError("MAIL_SMTP_HOST is not configured.")
        if not request.from_email:
            raise MailProviderError("MAIL_FROM_EMAIL is not configured.")
        if settings.MAIL_SMTP_SSL and settings.MAIL_SMTP_STARTTLS:
            raise MailProviderError("MAIL_SMTP_SSL and MAIL_SMTP_STARTTLS cannot both be enabled.")
        if bool(settings.MAIL_SMTP_USERNAME) != bool(settings.MAIL_SMTP_PASSWORD):
            raise MailProviderError(
                "MAIL_SMTP_USERNAME and MAIL_SMTP_PASSWORD must both be set for SMTP auth."
            )

        message = EmailMessage()
        message["From"] = formataddr((request.from_name, request.from_email))
        message["To"] = request.recipient_email
        message["Subject"] = request.subject
        if request.reply_to:
            message["Reply-To"] = request.reply_to

        message_id = make_msgid(domain=request.from_email.split("@", 1)[-1])
        message["Message-ID"] = message_id
        message.set_content(request.body)

        try:
            if settings.MAIL_SMTP_SSL:
                with smtplib.SMTP_SSL(
                    settings.MAIL_SMTP_HOST,
                    settings.MAIL_SMTP_PORT,
                    timeout=request.timeout_seconds,
                ) as server:
                    self._login(server)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    settings.MAIL_SMTP_HOST,
                    settings.MAIL_SMTP_PORT,
                    timeout=request.timeout_seconds,
                ) as server:
                    server.ehlo()
                    if settings.MAIL_SMTP_STARTTLS:
                        server.starttls()
                        server.ehlo()
                    self._login(server)
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
    def _login(server: smtplib.SMTP) -> None:
        if settings.MAIL_SMTP_USERNAME and settings.MAIL_SMTP_PASSWORD:
            server.login(settings.MAIL_SMTP_USERNAME, settings.MAIL_SMTP_PASSWORD)
