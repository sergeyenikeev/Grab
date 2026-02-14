from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.utils import getaddresses
from typing import Any

from googleapiclient.discovery import build

from grab.parsers.utils import extract_links
from grab.sources.models import AttachmentData, EmailMessageData

from .auth import GmailAuthManager


class GmailEmailSource:
    def __init__(self, auth_manager: GmailAuthManager, account: str | None = None):
        self.auth_manager = auth_manager
        self.account = account

    def _decode_b64(self, value: str | None) -> str:
        if not value:
            return ""
        data = base64.urlsafe_b64decode(value.encode("utf-8"))
        return data.decode("utf-8", errors="replace")

    def _extract_headers(self, payload: dict[str, Any]) -> dict[str, str]:
        headers = payload.get("headers", [])
        result: dict[str, str] = {}
        for item in headers:
            name = item.get("name")
            if name:
                result[name.lower()] = item.get("value", "")
        return result

    def _collect_parts(
        self,
        message_id: str,
        payload: dict[str, Any],
        users_resource,
    ) -> tuple[str, str, list[AttachmentData]]:  # noqa: ANN001
        text_body = ""
        html_body = ""
        attachments: list[AttachmentData] = []

        def walk(part: dict[str, Any]) -> None:
            nonlocal text_body, html_body
            mime_type = part.get("mimeType", "")
            filename = part.get("filename")
            body = part.get("body", {})
            data = body.get("data")
            attachment_id = body.get("attachmentId")

            if mime_type == "text/plain" and data:
                text_body += self._decode_b64(data)
            elif mime_type == "text/html" and data:
                html_body += self._decode_b64(data)
            elif filename and attachment_id:
                attachment_payload = (
                    users_resource.messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=attachment_id)
                    .execute()
                )
                attachment_data = base64.urlsafe_b64decode(
                    attachment_payload.get("data", "").encode("utf-8")
                )
                attachments.append(
                    AttachmentData(filename=filename, content_type=mime_type, data=attachment_data)
                )

            for nested in part.get("parts", []):
                walk(nested)

        walk(payload)
        return text_body, html_body, attachments

    def fetch_messages(
        self,
        keywords: list[str],
        since: datetime | None = None,
        max_messages: int = 200,
    ) -> list[EmailMessageData]:
        creds = self.auth_manager.ensure_credentials()
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)

        query_parts = ["(" + " OR ".join(keywords) + ")"]
        if since:
            query_parts.append(f"after:{since.strftime('%Y/%m/%d')}")
        query = " ".join(query_parts)

        users = service.users()
        request = users.messages().list(userId="me", q=query, maxResults=min(max_messages, 500))
        messages_meta: list[dict[str, Any]] = []
        while request is not None and len(messages_meta) < max_messages:
            response = request.execute()
            messages_meta.extend(response.get("messages", []))
            if len(messages_meta) >= max_messages:
                break
            request = users.messages().list_next(request, response)

        result: list[EmailMessageData] = []
        for message_meta in messages_meta[:max_messages]:
            message_id = message_meta["id"]
            payload = users.messages().get(userId="me", id=message_id, format="full").execute()

            parsed_payload = payload.get("payload", {})
            headers = self._extract_headers(parsed_payload)
            text_body, html_body, attachments = self._collect_parts(message_id, parsed_payload, users)

            if not text_body and payload.get("snippet"):
                text_body = payload["snippet"]

            sender = headers.get("from")
            recipients = [addr for _, addr in getaddresses([headers.get("to", "")]) if addr]

            internal_date = payload.get("internalDate")
            sent_at = None
            if internal_date:
                sent_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

            links = extract_links(text_body, html_body)

            result.append(
                EmailMessageData(
                    source="gmail_api",
                    provider="gmail",
                    account=self.account,
                    message_id=headers.get("message-id", message_id),
                    thread_id=payload.get("threadId"),
                    subject=headers.get("subject"),
                    sender=sender,
                    recipients=recipients,
                    sent_at=sent_at,
                    text_body=text_body,
                    html_body=html_body,
                    links=links,
                    attachments=attachments,
                    raw_payload=payload,
                )
            )

        return result
