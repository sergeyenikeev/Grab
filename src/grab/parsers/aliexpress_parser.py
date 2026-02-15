from __future__ import annotations

import re

from grab.core.normalize import NormalizedItem, NormalizedOrder
from grab.sources.models import EmailMessageData

from .utils import filter_media_links

ORDER_ID_PATTERNS = [
    re.compile(r"(?:order\s*id|order\s*no\.?|заказ|номер\s*заказа)\s*[:#№-]*\s*([0-9A-Z-]{6,})", re.IGNORECASE),
    re.compile(r"aliexpress\s*order\s*#\s*([0-9A-Z-]{6,})", re.IGNORECASE),
]


def _extract_order_id(text: str) -> str | None:
    for pattern in ORDER_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def parse_aliexpress_message(message: EmailMessageData) -> NormalizedOrder | None:
    text_blob = "\n".join(part for part in [message.subject, message.text_body, message.html_body] if part)
    if not text_blob.strip():
        return None

    external_order_id = _extract_order_id(text_blob)
    items: list[NormalizedItem] = []

    # Базовый шаблон: если нет распознанных строк товара, используем тему письма.
    if message.subject:
        items.append(
            NormalizedItem(
                external_item_id=None,
                title_full=message.subject.strip(),
                title_short=message.subject.strip()[:120],
                quantity=1.0,
            )
        )

    media_links = filter_media_links(message.links)
    for item in items:
        item.media_urls.extend(media_links)

    source_url = next((link for link in message.links if "http" in link), None)

    return NormalizedOrder(
        store_code="aliexpress",
        store_name="AliExpress",
        external_order_id=external_order_id,
        source_message_id=message.message_id,
        order_datetime=message.sent_at,
        source_url=source_url,
        items=items,
    )
