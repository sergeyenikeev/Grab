from datetime import datetime, timezone

from grab.core.dedupe import build_item_dedupe_key, build_order_dedupe_key


def test_order_key_uses_external_order_id() -> None:
    key1 = build_order_dedupe_key("ozon", "12345")
    key2 = build_order_dedupe_key("ozon", "12345")
    assert key1 == key2


def test_order_key_fallback_message_id() -> None:
    key1 = build_order_dedupe_key("ozon", None, email_message_id="msg-1")
    key2 = build_order_dedupe_key("ozon", None, email_message_id="msg-1")
    assert key1 == key2


def test_item_key_fallback_heuristic() -> None:
    dt = datetime(2026, 2, 10, tzinfo=timezone.utc)
    key1 = build_item_dedupe_key(
        store_code="ozon",
        external_item_id=None,
        sku="ABC-1",
        order_date=dt,
        unit_price=100.0,
        quantity=2,
    )
    key2 = build_item_dedupe_key(
        store_code="ozon",
        external_item_id=None,
        sku="ABC-1",
        order_date=dt,
        unit_price=100.0,
        quantity=2,
    )
    assert key1 == key2
