from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class NormalizedAttribute:
    key: str
    value_type: str
    value_text: str | None = None
    value_number: float | None = None
    value_bool: bool | None = None
    value_json_raw: str | None = None
    source: str | None = None


@dataclass(slots=True)
class NormalizedItem:
    external_item_id: str | None
    title_full: str
    title_short: str | None = None
    store_category_path: str | None = None
    unified_category_path: str | None = None
    brand: str | None = None
    model: str | None = None
    sku: str | None = None
    quantity: float = 1.0
    unit_price: float | None = None
    discount_amount: float | None = None
    shipping_amount: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    product_url: str | None = None
    order_url: str | None = None
    receipt_url: str | None = None
    attributes: list[NormalizedAttribute] = field(default_factory=list)
    media_urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class NormalizedOrder:
    store_code: str
    store_name: str
    external_order_id: str | None
    source_message_id: str | None
    order_datetime: datetime | None = None
    paid_datetime: datetime | None = None
    delivered_datetime: datetime | None = None
    currency: str | None = None
    subtotal_amount: float | None = None
    shipping_amount: float | None = None
    discount_amount: float | None = None
    total_amount: float | None = None
    status: str | None = None
    source_url: str | None = None
    items: list[NormalizedItem] = field(default_factory=list)
    seller_name: str | None = None
    seller_inn: str | None = None
    seller_legal_entity: str | None = None
