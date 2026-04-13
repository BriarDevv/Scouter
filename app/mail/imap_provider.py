from __future__ import annotations

import contextlib
import html
import imaplib
import re
import shlex
from datetime import UTC, datetime
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from typing import cast

from app.core.config import settings
from app.mail.inbound_provider import InboundMailMessage, InboundMailProviderError

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


class IMAPInboundMailProvider:
    name = "imap"

    def list_messages(self, *, limit: int) -> list[InboundMailMessage]:
        if not settings.MAIL_IMAP_HOST:
            raise InboundMailProviderError("MAIL_IMAP_HOST is not configured.")
        if not settings.MAIL_IMAP_USERNAME or not settings.MAIL_IMAP_PASSWORD:
            raise InboundMailProviderError(
                "MAIL_IMAP_USERNAME and MAIL_IMAP_PASSWORD must both be configured."
            )

        try:
            connection = self._connect()
            try:
                self._login_and_select(connection)
                uids = self._search_message_uids(connection)
                if limit > 0:
                    uids = uids[-limit:]

                messages: list[InboundMailMessage] = []
                for uid in reversed(uids):
                    payload = self._fetch_message(connection, uid)
                    if payload is not None:
                        messages.append(payload)
                return messages
            finally:
                with contextlib.suppress(imaplib.IMAP4.error):
                    connection.logout()
        except (OSError, imaplib.IMAP4.error) as exc:
            raise InboundMailProviderError(str(exc)) from exc

    def _connect(self) -> imaplib.IMAP4:
        host = settings.MAIL_IMAP_HOST
        if host is None:
            raise InboundMailProviderError("MAIL_IMAP_HOST must be set before connecting")
        if settings.MAIL_IMAP_SSL:
            return imaplib.IMAP4_SSL(
                host,
                settings.MAIL_IMAP_PORT,
                timeout=settings.MAIL_INBOUND_TIMEOUT,
            )
        return imaplib.IMAP4(
            host,
            settings.MAIL_IMAP_PORT,
            timeout=settings.MAIL_INBOUND_TIMEOUT,
        )

    def _login_and_select(self, connection: imaplib.IMAP4) -> None:
        connection.login(settings.MAIL_IMAP_USERNAME or "", settings.MAIL_IMAP_PASSWORD or "")
        status, _ = connection.select(settings.MAIL_IMAP_MAILBOX, readonly=True)
        if status != "OK":
            raise InboundMailProviderError(
                f"Unable to select mailbox {settings.MAIL_IMAP_MAILBOX!r}."
            )

    def _search_message_uids(self, connection: imaplib.IMAP4) -> list[str]:
        criteria = settings.MAIL_IMAP_SEARCH_CRITERIA.strip() or "ALL"
        search_terms = shlex.split(criteria)
        status, data = connection.uid("search", None, *search_terms)  # type: ignore[arg-type]  # imaplib stubs don't accept None charset
        if status != "OK":
            raise InboundMailProviderError("Unable to search mailbox.")
        if not data or not data[0]:
            return []
        return [uid.decode("utf-8") for uid in data[0].split() if uid]

    def _fetch_message(self, connection: imaplib.IMAP4, uid: str) -> InboundMailMessage | None:
        status, data = connection.uid("fetch", uid, "(BODY.PEEK[] INTERNALDATE)")
        if status != "OK":
            raise InboundMailProviderError(f"Unable to fetch message UID {uid}.")

        raw_message = None
        internal_date: datetime | None = None
        for item in data:
            if not isinstance(item, tuple):
                continue
            metadata = item[0]
            raw_message = item[1]
            if isinstance(metadata, bytes):
                parsed = imaplib.Internaldate2tuple(metadata)
                if parsed is not None:
                    internal_date = datetime(*parsed[:6], tzinfo=UTC)
            if raw_message:
                break

        if not raw_message:
            return None

        message = cast(EmailMessage, message_from_bytes(raw_message, policy=default_policy))
        body_text = self._extract_body_text(message)
        body_snippet = self._build_snippet(body_text)
        from_name, from_email = parseaddr(message.get("From", ""))
        recipients = [email for _, email in getaddresses(message.get_all("To", [])) if email]

        received_at = self._parse_received_at(message.get("Date")) or internal_date

        return InboundMailMessage(
            provider=self.name,
            provider_mailbox=settings.MAIL_IMAP_MAILBOX,
            provider_message_id=uid,
            message_id=self._clean_header_value(message.get("Message-ID")),
            in_reply_to=self._clean_header_value(message.get("In-Reply-To")),
            references_raw=self._clean_header_value(message.get("References")),
            from_email=from_email or None,
            from_name=from_name or None,
            to_email=", ".join(recipients) if recipients else None,
            subject=self._clean_header_value(message.get("Subject")),
            body_text=body_text,
            body_snippet=body_snippet,
            received_at=received_at,
            raw_metadata={
                "uid": uid,
                "date_header": message.get("Date"),
                "references": self._clean_header_value(message.get("References")),
            },
        )

    @staticmethod
    def _parse_received_at(date_header: str | None) -> datetime | None:
        if not date_header:
            return None
        try:
            parsed = parsedate_to_datetime(date_header)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _extract_body_text(cls, message: EmailMessage) -> str | None:
        if message.is_multipart():
            plain_parts: list[str] = []
            html_parts: list[str] = []
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = (part.get_content_disposition() or "").lower()
                if disposition == "attachment":
                    continue
                try:
                    content = part.get_content()
                except (LookupError, ValueError):
                    continue
                if not isinstance(content, str):
                    continue
                if content_type == "text/plain":
                    plain_parts.append(content)
                elif content_type == "text/html":
                    html_parts.append(content)

            if plain_parts:
                return cls._normalize_text("\n\n".join(plain_parts))
            if html_parts:
                return cls._normalize_text(cls._strip_html("\n\n".join(html_parts)))
            return None

        try:
            content = message.get_content()
        except (LookupError, ValueError):
            return None
        if not isinstance(content, str):
            return None
        if message.get_content_type() == "text/html":
            return cls._normalize_text(cls._strip_html(content))
        return cls._normalize_text(content)

    @staticmethod
    def _strip_html(content: str) -> str:
        return html.unescape(TAG_RE.sub(" ", content))

    @staticmethod
    def _normalize_text(content: str | None) -> str | None:
        if not content:
            return None
        normalized = content.replace("\r", "\n")
        normalized = WHITESPACE_RE.sub(" ", normalized).strip()
        return normalized or None

    @classmethod
    def _build_snippet(cls, content: str | None, limit: int = 280) -> str | None:
        normalized = cls._normalize_text(content)
        if not normalized:
            return None
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"

    @staticmethod
    def _clean_header_value(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
