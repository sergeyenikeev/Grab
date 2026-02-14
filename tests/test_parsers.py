from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from grab.parsers import parse_email_to_orders
from grab.sources.models import EmailMessageData


@pytest.mark.parametrize(
    ("fixture_name", "subject", "sender", "store_code"),
    [
        ("ozon.txt", "Ozon: заказ №12345678", "info@ozon.ru", "ozon"),
        ("wildberries.txt", "Wildberries заказ WB-987654", "info@wildberries.ru", "wildberries"),
        (
            "yamarket.txt",
            "Яндекс Маркет: заказ YM-001122",
            "market@yandex.ru",
            "yamarket",
        ),
    ],
)
def test_email_parser_detects_store_and_items(
    fixture_name: str,
    subject: str,
    sender: str,
    store_code: str,
) -> None:
    body = (Path(__file__).parent / "fixtures" / "emails" / fixture_name).read_text(encoding="utf-8")
    message = EmailMessageData(
        source="test",
        provider="test",
        account="test@example.com",
        message_id="msg-1",
        thread_id=None,
        subject=subject,
        sender=sender,
        recipients=["you@example.com"],
        sent_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        text_body=body,
        html_body=None,
        links=["https://example.com/product.jpg"],
        attachments=[],
        raw_payload={},
    )

    orders = parse_email_to_orders(message)
    assert len(orders) == 1
    order = orders[0]
    assert order.store_code == store_code
    assert len(order.items) >= 1
    assert order.items[0].title_full
