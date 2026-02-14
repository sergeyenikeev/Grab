from __future__ import annotations

import re
from datetime import datetime

from grab.core.normalize import NormalizedAttribute, NormalizedItem, NormalizedOrder
from grab.sources.models import EmailMessageData

from .utils import filter_media_links

ORDER_ID_PATTERNS = [
    re.compile(r"(?:заказ|order|№)\s*[#:№-]*\s*([A-Za-zА-Яа-я0-9-]{5,})", re.IGNORECASE),
    re.compile(r"номер\s*заказа\s*[:№-]*\s*([A-Za-zА-Яа-я0-9-]{5,})", re.IGNORECASE),
]
PRICE_PATTERN = re.compile(r"(\d[\d\s.,]*)\s*(?:₽|руб|RUB)", re.IGNORECASE)
ITEM_LINE_PATTERN = re.compile(
    r"^[\-•\*\d\)\.]\s*(?P<title>.+?)(?:,|\s+-\s+|\s+x\s+)(?:(?P<qty>\d+(?:[.,]\d+)?)\s*(?:шт|pcs|x)?)?(?:.*?(?P<price>\d[\d\s.,]*)\s*(?:₽|руб|RUB))?",
    re.IGNORECASE,
)

STORE_MAP = {
    "ozon": ("ozon", "Ozon"),
    "wildberries": ("wildberries", "Wildberries"),
    "wb": ("wildberries", "Wildberries"),
    "яндекс маркет": ("yamarket", "Яндекс Маркет"),
    "yandex market": ("yamarket", "Яндекс Маркет"),
    "market.yandex": ("yamarket", "Яндекс Маркет"),
    "мегамаркет": ("megamarket", "Мегамаркет"),
    "dns": ("dns", "DNS"),
    "ашан": ("auchan", "Ашан"),
}


def _safe_float(value: str | None) -> float | None:
    if not value:
        return None
    normalized = value.replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _detect_store(message: EmailMessageData) -> tuple[str, str]:
    blob = " ".join(
        part or "" for part in [message.subject, message.sender, message.text_body, message.html_body]
    ).lower()

    for marker, store_pair in STORE_MAP.items():
        if marker in blob:
            return store_pair

    return "email_other", "Email/прочее"


def _extract_order_id(text: str) -> str | None:
    for pattern in ORDER_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _extract_total_amount(text: str) -> float | None:
    for line in text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in ["итог", "итого", "к оплате", "total"]):
            price_match = PRICE_PATTERN.search(line)
            if price_match:
                return _safe_float(price_match.group(1))
    first = PRICE_PATTERN.search(text)
    if first:
        return _safe_float(first.group(1))
    return None


def _guess_currency(text: str) -> str | None:
    lowered = text.lower()
    if "₽" in lowered or "руб" in lowered:
        return "RUB"
    if "usd" in lowered or "$" in lowered:
        return "USD"
    if "eur" in lowered or "€" in lowered:
        return "EUR"
    return None


def _build_short_title(title: str) -> str:
    title = title.strip()
    for splitter in [",", " - ", " ("]:
        if splitter in title:
            return title.split(splitter)[0].strip()[:120]
    return title[:120]


def _parse_items_from_text(text: str) -> list[NormalizedItem]:
    items: list[NormalizedItem] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = ITEM_LINE_PATTERN.match(line)
        if not match:
            continue

        title = match.group("title")
        if not title:
            continue
        qty = _safe_float(match.group("qty")) or 1.0
        price = _safe_float(match.group("price"))

        items.append(
            NormalizedItem(
                external_item_id=None,
                title_full=title.strip(),
                title_short=_build_short_title(title),
                quantity=qty,
                unit_price=price,
                total_amount=(price * qty) if price is not None else None,
                attributes=[],
            )
        )

    return items


def _fallback_single_item(subject: str | None, total_amount: float | None, currency: str | None) -> NormalizedItem:
    title = subject or "Покупка из письма"
    return NormalizedItem(
        external_item_id=None,
        title_full=title,
        title_short=_build_short_title(title),
        quantity=1,
        unit_price=total_amount,
        total_amount=total_amount,
        currency=currency,
        attributes=[NormalizedAttribute(key="source", value_type="text", value_text="email_fallback")],
    )


def parse_email_to_orders(message: EmailMessageData) -> list[NormalizedOrder]:
    text_blob = "\n".join(part for part in [message.subject, message.text_body, message.html_body] if part)
    if not text_blob.strip():
        return []

    store_code, store_name = _detect_store(message)
    external_order_id = _extract_order_id(text_blob)
    total_amount = _extract_total_amount(text_blob)
    currency = _guess_currency(text_blob)
    items = _parse_items_from_text(message.text_body or "")
    if not items:
        items = [_fallback_single_item(message.subject, total_amount, currency)]

    media_links = filter_media_links(message.links)
    for item in items:
        item.currency = item.currency or currency
        item.media_urls.extend(media_links)

    source_url = next((link for link in message.links if "http" in link), None)

    order = NormalizedOrder(
        store_code=store_code,
        store_name=store_name,
        external_order_id=external_order_id,
        source_message_id=message.message_id,
        order_datetime=message.sent_at if isinstance(message.sent_at, datetime) else None,
        currency=currency,
        total_amount=total_amount,
        source_url=source_url,
        items=items,
    )
    return [order]
