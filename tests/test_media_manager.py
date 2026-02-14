from __future__ import annotations

from pathlib import Path

from grab.core.media import MediaManager


def _create_order_and_items(repository) -> tuple[int, int, int]:  # noqa: ANN001
    store_id = repository.upsert_store("ozon", "Ozon")
    account_id = repository.upsert_account("gmail", "me@gmail.com", "me@gmail.com")
    order_id = repository.upsert_order(
        store_id=store_id,
        account_id=account_id,
        seller_id=None,
        external_order_id="A1",
        dedupe_key="order-a1",
        order_datetime="2026-02-01T10:00:00+00:00",
        paid_datetime=None,
        delivered_datetime=None,
        currency="RUB",
        subtotal_amount=100,
        shipping_amount=0,
        discount_amount=0,
        total_amount=100,
        status="ok",
        source_url=None,
        raw_ref="1",
    )
    item1 = repository.upsert_order_item(
        order_id=order_id,
        external_item_id="i1",
        dedupe_key="i1",
        product_id=None,
        title_full="Товар 1",
        title_short="Товар",
        store_category_path=None,
        unified_category_path=None,
        brand=None,
        model=None,
        sku=None,
        quantity=1,
        unit_price=100,
        discount_amount=0,
        shipping_amount=0,
        total_amount=100,
        currency="RUB",
        product_url=None,
        order_url=None,
        receipt_url=None,
    )
    item2 = repository.upsert_order_item(
        order_id=order_id,
        external_item_id="i2",
        dedupe_key="i2",
        product_id=None,
        title_full="Товар 2",
        title_short="Товар",
        store_category_path=None,
        unified_category_path=None,
        brand=None,
        model=None,
        sku=None,
        quantity=1,
        unit_price=100,
        discount_amount=0,
        shipping_amount=0,
        total_amount=100,
        currency="RUB",
        product_url=None,
        order_url=None,
        receipt_url=None,
    )
    return order_id, item1, item2


def test_media_manager_dedup_by_sha(repository, tmp_path: Path) -> None:  # noqa: ANN001
    order_id, item1, item2 = _create_order_and_items(repository)
    media_root = tmp_path / "media"
    manager = MediaManager(repository=repository, media_root=media_root)

    content = b"same-content-for-two-items"

    path1 = manager.save_bytes(
        store_code="ozon",
        order_ref=str(order_id),
        item_id=item1,
        filename="photo.jpg",
        content=content,
        mime="image/jpeg",
        source_url="https://example.com/a.jpg",
        source="test",
    )
    path2 = manager.save_bytes(
        store_code="ozon",
        order_ref=str(order_id),
        item_id=item2,
        filename="photo-copy.jpg",
        content=content,
        mime="image/jpeg",
        source_url="https://example.com/b.jpg",
        source="test",
    )

    assert Path(path1).exists()
    assert Path(path2).exists()
    assert path1 == path2

    files = [p for p in media_root.rglob("*") if p.is_file() and p.name != "meta.json"]
    assert len(files) == 1

    media_count = repository.connection.execute("SELECT COUNT(*) AS cnt FROM media").fetchone()["cnt"]
    assert media_count == 2
