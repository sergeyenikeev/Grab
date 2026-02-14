from __future__ import annotations


def test_db_upsert_order_is_idempotent(repository) -> None:  # noqa: ANN001
    store_id = repository.upsert_store("ozon", "Ozon")
    account_id = repository.upsert_account("gmail", "me@gmail.com", "me@gmail.com")

    order_id_1 = repository.upsert_order(
        store_id=store_id,
        account_id=account_id,
        seller_id=None,
        external_order_id="123",
        dedupe_key="dedupe-order-123",
        order_datetime="2026-02-01T10:00:00+00:00",
        paid_datetime=None,
        delivered_datetime=None,
        currency="RUB",
        subtotal_amount=1000.0,
        shipping_amount=0.0,
        discount_amount=0.0,
        total_amount=1000.0,
        status="created",
        source_url="https://ozon.ru/order/123",
        raw_ref="1",
    )

    order_id_2 = repository.upsert_order(
        store_id=store_id,
        account_id=account_id,
        seller_id=None,
        external_order_id="123",
        dedupe_key="dedupe-order-123",
        order_datetime="2026-02-01T10:00:00+00:00",
        paid_datetime=None,
        delivered_datetime=None,
        currency="RUB",
        subtotal_amount=1000.0,
        shipping_amount=0.0,
        discount_amount=0.0,
        total_amount=900.0,
        status="paid",
        source_url="https://ozon.ru/order/123",
        raw_ref="2",
    )

    assert order_id_1 == order_id_2

    row = repository.connection.execute(
        "SELECT total_amount, status FROM orders WHERE id = ?",
        (order_id_1,),
    ).fetchone()
    assert row["total_amount"] == 900.0
    assert row["status"] == "paid"
