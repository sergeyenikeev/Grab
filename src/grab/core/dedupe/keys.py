from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Any


def _normalize_part(part: Any) -> str:
    if part is None:
        return ""
    if isinstance(part, datetime):
        return part.isoformat()
    if isinstance(part, Decimal):
        return format(part, "f")
    return str(part).strip().lower()


def stable_hash(*parts: Any) -> str:
    payload = "||".join(_normalize_part(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_order_dedupe_key(
    store_code: str,
    external_order_id: str | None,
    email_message_id: str | None = None,
    order_date: datetime | None = None,
    total_amount: float | None = None,
) -> str:
    if external_order_id:
        return stable_hash("order", store_code, external_order_id)
    if email_message_id:
        return stable_hash("order", store_code, email_message_id)
    return stable_hash("order", store_code, order_date, total_amount)


def build_item_dedupe_key(
    store_code: str,
    external_item_id: str | None,
    email_message_id: str | None = None,
    item_index: int | None = None,
    sku: str | None = None,
    order_date: datetime | None = None,
    unit_price: float | None = None,
    quantity: float | None = None,
) -> str:
    if external_item_id:
        return stable_hash("item", store_code, external_item_id)
    if email_message_id is not None and item_index is not None:
        return stable_hash("item", store_code, email_message_id, item_index)
    return stable_hash("item", store_code, sku, order_date, unit_price, quantity)


def build_product_canonical_key(
    brand: str | None,
    model: str | None,
    sku: str | None,
    title: str | None,
) -> str:
    return stable_hash("product", brand, model, sku, title)
