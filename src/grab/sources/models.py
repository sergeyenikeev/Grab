from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class AttachmentData:
    filename: str | None
    content_type: str | None
    data: bytes
    source_url: str | None = None


@dataclass(slots=True)
class EmailMessageData:
    source: str
    provider: str
    account: str | None
    message_id: str
    thread_id: str | None
    subject: str | None
    sender: str | None
    recipients: list[str] = field(default_factory=list)
    sent_at: datetime | None = None
    text_body: str | None = None
    html_body: str | None = None
    links: list[str] = field(default_factory=list)
    attachments: list[AttachmentData] = field(default_factory=list)
    raw_payload: dict | None = None
