from __future__ import annotations

import email
import imaplib
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime

from grab.config import ImapAccountConfig
from grab.parsers.utils import extract_links
from grab.sources.models import AttachmentData, EmailMessageData


class ImapEmailSource:
    def __init__(self, config: ImapAccountConfig):
        self.config = config

    @staticmethod
    def _decode_header(value: str | None) -> str:
        if not value:
            return ""
        decoded = decode_header(value)
        parts: list[str] = []
        for chunk, encoding in decoded:
            if isinstance(chunk, bytes):
                parts.append(chunk.decode(encoding or "utf-8", errors="replace"))
            else:
                parts.append(chunk)
        return "".join(parts)

    @staticmethod
    def _decode_part_payload(part: Message) -> str:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    def _extract_message_content(self, message: Message) -> tuple[str, str, list[AttachmentData]]:
        text_body = ""
        html_body = ""
        attachments: list[AttachmentData] = []

        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                content_disposition = (part.get("Content-Disposition") or "").lower()
                filename = self._decode_header(part.get_filename()) if part.get_filename() else None

                if "attachment" in content_disposition or filename:
                    data = part.get_payload(decode=True)
                    if data:
                        attachments.append(
                            AttachmentData(
                                filename=filename,
                                content_type=content_type,
                                data=data,
                            )
                        )
                    continue

                if content_type == "text/plain" and not text_body:
                    text_body = self._decode_part_payload(part)
                elif content_type == "text/html" and not html_body:
                    html_body = self._decode_part_payload(part)
        else:
            content_type = message.get_content_type()
            if content_type == "text/plain":
                text_body = self._decode_part_payload(message)
            elif content_type == "text/html":
                html_body = self._decode_part_payload(message)

        return text_body, html_body, attachments

    def check_connection(self) -> None:
        with imaplib.IMAP4_SSL(self.config.host, self.config.port) as client:
            client.login(self.config.username, self.config.password)
            client.select(self.config.mailbox)

    def fetch_messages(
        self,
        keywords: list[str],
        since: datetime | None = None,
        max_messages: int = 300,
    ) -> list[EmailMessageData]:
        if since and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)

        with imaplib.IMAP4_SSL(self.config.host, self.config.port) as client:
            client.login(self.config.username, self.config.password)
            client.select(self.config.mailbox)

            criteria = ["ALL"]
            if since:
                criteria.append(f'SINCE "{since.strftime("%d-%b-%Y")}"')

            status, data = client.search(None, *criteria)
            if status != "OK":
                return []

            message_ids = data[0].split()
            message_ids = message_ids[-max_messages:]

            result: list[EmailMessageData] = []
            keywords_lower = [k.lower() for k in keywords]

            for msg_id in reversed(message_ids):
                fetch_status, fetch_data = client.fetch(msg_id, "(RFC822)")
                if fetch_status != "OK" or not fetch_data:
                    continue

                raw_bytes = fetch_data[0][1]
                mime_msg = email.message_from_bytes(raw_bytes)

                subject = self._decode_header(mime_msg.get("Subject"))
                sender = self._decode_header(mime_msg.get("From"))
                recipients = [addr for _, addr in getaddresses([mime_msg.get("To", "")]) if addr]
                message_id_header = self._decode_header(mime_msg.get("Message-Id")) or msg_id.decode()

                date_header = mime_msg.get("Date")
                sent_at = None
                if date_header:
                    try:
                        sent_at = parsedate_to_datetime(date_header)
                    except (TypeError, ValueError):
                        sent_at = None

                text_body, html_body, attachments = self._extract_message_content(mime_msg)
                blob = " ".join([subject, sender, text_body, html_body]).lower()
                if keywords_lower and not any(keyword in blob for keyword in keywords_lower):
                    continue

                links = extract_links(text_body, html_body)

                result.append(
                    EmailMessageData(
                        source=f"imap_{self.config.provider}",
                        provider=self.config.provider,
                        account=self.config.username,
                        message_id=message_id_header,
                        thread_id=None,
                        subject=subject,
                        sender=sender,
                        recipients=recipients,
                        sent_at=sent_at,
                        text_body=text_body,
                        html_body=html_body,
                        links=links,
                        attachments=attachments,
                        raw_payload={"rfc822_size": len(raw_bytes)},
                    )
                )

        return result
