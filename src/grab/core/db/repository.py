from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .migrations import apply_migrations, connect_db


class GrabRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = connect_db(db_path)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> GrabRepository:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()

    def migrate(self) -> list[str]:
        migrations_dir = Path(__file__).parent / "migrations"
        return apply_migrations(self.connection, migrations_dir)

    @staticmethod
    def _to_json(payload: dict[str, Any] | list[Any] | None) -> str | None:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False)

    def _fetch_id(self, query: str, params: tuple[Any, ...]) -> int:
        row = self.connection.execute(query, params).fetchone()
        if row is None:
            raise RuntimeError(f"Не найден идентификатор по запросу: {query}")
        return int(row["id"])

    def upsert_store(self, code: str, name: str, website: str | None = None) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO stores (code, name, website)
                VALUES (?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    website = COALESCE(excluded.website, stores.website)
                """,
                (code, name, website),
            )
        return self._fetch_id("SELECT id FROM stores WHERE code = ?", (code,))

    def upsert_account(
        self,
        provider: str,
        account_identifier: str,
        display_name: str | None = None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO accounts (provider, account_identifier, display_name)
                VALUES (?, ?, ?)
                ON CONFLICT(provider, account_identifier) DO UPDATE SET
                    display_name = COALESCE(excluded.display_name, accounts.display_name)
                """,
                (provider, account_identifier, display_name),
            )
        return self._fetch_id(
            "SELECT id FROM accounts WHERE provider = ? AND account_identifier = ?",
            (provider, account_identifier),
        )

    def upsert_seller(
        self,
        store_id: int,
        name: str,
        inn: str | None = None,
        legal_entity: str | None = None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO sellers (store_id, name, inn, legal_entity)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(store_id, name, inn) DO UPDATE SET
                    legal_entity = COALESCE(excluded.legal_entity, sellers.legal_entity)
                """,
                (store_id, name, inn, legal_entity),
            )
        return self._fetch_id(
            "SELECT id FROM sellers WHERE store_id = ? AND name = ? AND ifnull(inn, '') = ifnull(?, '')",
            (store_id, name, inn),
        )

    def start_sync_run(self, correlation_id: str, source: str, started_at: str) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO sync_runs (correlation_id, source, started_at, status)
                VALUES (?, ?, ?, 'running')
                ON CONFLICT(correlation_id) DO UPDATE SET
                    source = excluded.source,
                    started_at = excluded.started_at,
                    status = 'running',
                    finished_at = NULL,
                    stats_json = NULL,
                    error_text = NULL
                """,
                (correlation_id, source, started_at),
            )
        return self._fetch_id(
            "SELECT id FROM sync_runs WHERE correlation_id = ?",
            (correlation_id,),
        )

    def finish_sync_run(
        self,
        correlation_id: str,
        finished_at: str,
        status: str,
        stats: dict[str, Any] | None,
        error_text: str | None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                UPDATE sync_runs
                SET finished_at = ?, status = ?, stats_json = ?, error_text = ?
                WHERE correlation_id = ?
                """,
                (finished_at, status, self._to_json(stats), error_text, correlation_id),
            )

    def upsert_raw_message(
        self,
        source: str,
        account_id: int | None,
        external_message_id: str,
        thread_id: str | None,
        message_datetime: str | None,
        subject: str | None,
        sender: str | None,
        recipients: str | None,
        raw_text: str | None,
        raw_html: str | None,
        raw_json: dict[str, Any] | None,
        raw_eml_path: str | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO raw_messages (
                    source, account_id, external_message_id, thread_id, message_datetime,
                    subject, sender, recipients, raw_text, raw_html, raw_json, raw_eml_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, external_message_id) DO UPDATE SET
                    thread_id = COALESCE(excluded.thread_id, raw_messages.thread_id),
                    message_datetime = COALESCE(excluded.message_datetime, raw_messages.message_datetime),
                    subject = COALESCE(excluded.subject, raw_messages.subject),
                    sender = COALESCE(excluded.sender, raw_messages.sender),
                    recipients = COALESCE(excluded.recipients, raw_messages.recipients),
                    raw_text = COALESCE(excluded.raw_text, raw_messages.raw_text),
                    raw_html = COALESCE(excluded.raw_html, raw_messages.raw_html),
                    raw_json = COALESCE(excluded.raw_json, raw_messages.raw_json),
                    raw_eml_path = COALESCE(excluded.raw_eml_path, raw_messages.raw_eml_path)
                """,
                (
                    source,
                    account_id,
                    external_message_id,
                    thread_id,
                    message_datetime,
                    subject,
                    sender,
                    recipients,
                    raw_text,
                    raw_html,
                    self._to_json(raw_json),
                    raw_eml_path,
                ),
            )
        return self._fetch_id(
            "SELECT id FROM raw_messages WHERE source = ? AND external_message_id = ?",
            (source, external_message_id),
        )

    def upsert_product(
        self,
        canonical_key: str,
        title_full: str | None,
        title_short: str | None,
        brand: str | None,
        model: str | None,
        sku: str | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO products (canonical_key, title_full, title_short, brand, model, sku)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_key) DO UPDATE SET
                    title_full = COALESCE(excluded.title_full, products.title_full),
                    title_short = COALESCE(excluded.title_short, products.title_short),
                    brand = COALESCE(excluded.brand, products.brand),
                    model = COALESCE(excluded.model, products.model),
                    sku = COALESCE(excluded.sku, products.sku),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (canonical_key, title_full, title_short, brand, model, sku),
            )
        return self._fetch_id("SELECT id FROM products WHERE canonical_key = ?", (canonical_key,))

    def upsert_order(
        self,
        store_id: int,
        account_id: int | None,
        seller_id: int | None,
        external_order_id: str | None,
        dedupe_key: str,
        order_datetime: str | None,
        paid_datetime: str | None,
        delivered_datetime: str | None,
        currency: str | None,
        subtotal_amount: float | None,
        shipping_amount: float | None,
        discount_amount: float | None,
        total_amount: float | None,
        status: str | None,
        source_url: str | None,
        raw_ref: str | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO orders (
                    store_id, account_id, seller_id, external_order_id, dedupe_key,
                    order_datetime, paid_datetime, delivered_datetime, currency,
                    subtotal_amount, shipping_amount, discount_amount, total_amount,
                    status, source_url, raw_ref
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key) DO UPDATE SET
                    account_id = COALESCE(excluded.account_id, orders.account_id),
                    seller_id = COALESCE(excluded.seller_id, orders.seller_id),
                    external_order_id = COALESCE(excluded.external_order_id, orders.external_order_id),
                    order_datetime = COALESCE(excluded.order_datetime, orders.order_datetime),
                    paid_datetime = COALESCE(excluded.paid_datetime, orders.paid_datetime),
                    delivered_datetime = COALESCE(excluded.delivered_datetime, orders.delivered_datetime),
                    currency = COALESCE(excluded.currency, orders.currency),
                    subtotal_amount = COALESCE(excluded.subtotal_amount, orders.subtotal_amount),
                    shipping_amount = COALESCE(excluded.shipping_amount, orders.shipping_amount),
                    discount_amount = COALESCE(excluded.discount_amount, orders.discount_amount),
                    total_amount = COALESCE(excluded.total_amount, orders.total_amount),
                    status = COALESCE(excluded.status, orders.status),
                    source_url = COALESCE(excluded.source_url, orders.source_url),
                    raw_ref = COALESCE(excluded.raw_ref, orders.raw_ref),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    store_id,
                    account_id,
                    seller_id,
                    external_order_id,
                    dedupe_key,
                    order_datetime,
                    paid_datetime,
                    delivered_datetime,
                    currency,
                    subtotal_amount,
                    shipping_amount,
                    discount_amount,
                    total_amount,
                    status,
                    source_url,
                    raw_ref,
                ),
            )
        return self._fetch_id("SELECT id FROM orders WHERE dedupe_key = ?", (dedupe_key,))

    def upsert_order_item(
        self,
        order_id: int,
        external_item_id: str | None,
        dedupe_key: str,
        product_id: int | None,
        title_full: str,
        title_short: str | None,
        store_category_path: str | None,
        unified_category_path: str | None,
        brand: str | None,
        model: str | None,
        sku: str | None,
        quantity: float,
        unit_price: float | None,
        discount_amount: float | None,
        shipping_amount: float | None,
        total_amount: float | None,
        currency: str | None,
        product_url: str | None,
        order_url: str | None,
        receipt_url: str | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO order_items (
                    order_id, external_item_id, dedupe_key, product_id,
                    title_full, title_short, store_category_path, unified_category_path,
                    brand, model, sku, quantity, unit_price, discount_amount, shipping_amount,
                    total_amount, currency, product_url, order_url, receipt_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id, dedupe_key) DO UPDATE SET
                    external_item_id = COALESCE(excluded.external_item_id, order_items.external_item_id),
                    product_id = COALESCE(excluded.product_id, order_items.product_id),
                    title_full = COALESCE(excluded.title_full, order_items.title_full),
                    title_short = COALESCE(excluded.title_short, order_items.title_short),
                    store_category_path = COALESCE(excluded.store_category_path, order_items.store_category_path),
                    unified_category_path = COALESCE(excluded.unified_category_path, order_items.unified_category_path),
                    brand = COALESCE(excluded.brand, order_items.brand),
                    model = COALESCE(excluded.model, order_items.model),
                    sku = COALESCE(excluded.sku, order_items.sku),
                    quantity = COALESCE(excluded.quantity, order_items.quantity),
                    unit_price = COALESCE(excluded.unit_price, order_items.unit_price),
                    discount_amount = COALESCE(excluded.discount_amount, order_items.discount_amount),
                    shipping_amount = COALESCE(excluded.shipping_amount, order_items.shipping_amount),
                    total_amount = COALESCE(excluded.total_amount, order_items.total_amount),
                    currency = COALESCE(excluded.currency, order_items.currency),
                    product_url = COALESCE(excluded.product_url, order_items.product_url),
                    order_url = COALESCE(excluded.order_url, order_items.order_url),
                    receipt_url = COALESCE(excluded.receipt_url, order_items.receipt_url),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    order_id,
                    external_item_id,
                    dedupe_key,
                    product_id,
                    title_full,
                    title_short,
                    store_category_path,
                    unified_category_path,
                    brand,
                    model,
                    sku,
                    quantity,
                    unit_price,
                    discount_amount,
                    shipping_amount,
                    total_amount,
                    currency,
                    product_url,
                    order_url,
                    receipt_url,
                ),
            )
        return self._fetch_id(
            "SELECT id FROM order_items WHERE order_id = ? AND dedupe_key = ?",
            (order_id, dedupe_key),
        )

    def upsert_product_attribute(
        self,
        product_id: int | None,
        item_id: int,
        attr_key: str,
        value_type: str,
        value_text: str | None,
        value_number: float | None,
        value_bool: bool | None,
        value_json_raw: str | None,
        source: str | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO product_attributes (
                    product_id, item_id, attr_key, value_type,
                    value_text, value_number, value_bool, value_json_raw, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id, attr_key, value_text, value_number, value_bool) DO UPDATE SET
                    value_json_raw = COALESCE(excluded.value_json_raw, product_attributes.value_json_raw),
                    source = COALESCE(excluded.source, product_attributes.source)
                """,
                (
                    product_id,
                    item_id,
                    attr_key,
                    value_type,
                    value_text,
                    value_number,
                    int(value_bool) if value_bool is not None else None,
                    value_json_raw,
                    source,
                ),
            )
        return self._fetch_id(
            """
            SELECT id FROM product_attributes
            WHERE item_id = ? AND attr_key = ? AND ifnull(value_text, '') = ifnull(?, '')
                AND ifnull(value_number, -99999999) = ifnull(?, -99999999)
                AND ifnull(value_bool, -1) = ifnull(?, -1)
            """,
            (
                item_id,
                attr_key,
                value_text,
                value_number,
                int(value_bool) if value_bool is not None else None,
            ),
        )

    def find_media_by_sha256(self, sha256_value: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM media WHERE sha256 = ? ORDER BY id LIMIT 1",
            (sha256_value,),
        ).fetchone()

    def upsert_media(
        self,
        related_item_id: int,
        source_url: str | None,
        local_path_abs: str,
        mime: str | None,
        sha256_value: str,
        size_bytes: int,
        source: str,
        meta_json: dict[str, Any] | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO media (
                    related_item_id, source_url, local_path_abs, mime,
                    sha256, size_bytes, source, meta_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(related_item_id, sha256, source_url) DO UPDATE SET
                    local_path_abs = excluded.local_path_abs,
                    mime = COALESCE(excluded.mime, media.mime),
                    size_bytes = COALESCE(excluded.size_bytes, media.size_bytes),
                    source = COALESCE(excluded.source, media.source),
                    meta_json = COALESCE(excluded.meta_json, media.meta_json),
                    downloaded_at = CURRENT_TIMESTAMP
                """,
                (
                    related_item_id,
                    source_url,
                    local_path_abs,
                    mime,
                    sha256_value,
                    size_bytes,
                    source,
                    self._to_json(meta_json),
                ),
            )
        return self._fetch_id(
            "SELECT id FROM media WHERE related_item_id = ? AND sha256 = ? AND ifnull(source_url, '') = ifnull(?, '')",
            (related_item_id, sha256_value, source_url),
        )

    def upsert_review(
        self,
        product_id: int | None,
        item_id: int | None,
        review_type: str,
        source: str | None,
        author: str | None,
        rating: float | None,
        review_date: str | None,
        text: str,
        url: str | None,
        helpful_count: int | None,
    ) -> int:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO reviews (
                    product_id, item_id, review_type, source, author,
                    rating, review_date, text, url, helpful_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id, review_type, source, author, review_date, text) DO UPDATE SET
                    rating = COALESCE(excluded.rating, reviews.rating),
                    url = COALESCE(excluded.url, reviews.url),
                    helpful_count = COALESCE(excluded.helpful_count, reviews.helpful_count)
                """,
                (
                    product_id,
                    item_id,
                    review_type,
                    source,
                    author,
                    rating,
                    review_date,
                    text,
                    url,
                    helpful_count,
                ),
            )
        return self._fetch_id(
            """
            SELECT id FROM reviews
            WHERE ifnull(product_id, -1) = ifnull(?, -1)
                AND review_type = ?
                AND ifnull(source, '') = ifnull(?, '')
                AND ifnull(author, '') = ifnull(?, '')
                AND ifnull(review_date, '') = ifnull(?, '')
                AND text = ?
            """,
            (product_id, review_type, source, author, review_date, text),
        )

    def count_public_reviews(self, product_id: int) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) as cnt FROM reviews WHERE product_id = ? AND review_type = 'public'",
            (product_id,),
        ).fetchone()
        return int(row["cnt"])

    def add_audit_log(
        self,
        correlation_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        before_json: dict[str, Any] | None,
        after_json: dict[str, Any] | None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO audit_log (correlation_id, entity_type, entity_id, action, before_json, after_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    correlation_id,
                    entity_type,
                    entity_id,
                    action,
                    self._to_json(before_json),
                    self._to_json(after_json),
                ),
            )

    def fetch_export_rows(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                o.id AS order_db_id,
                oi.id AS item_db_id,
                s.code AS store_code,
                s.name AS store_name,
                o.external_order_id,
                o.order_datetime,
                o.paid_datetime,
                o.delivered_datetime,
                o.currency,
                o.subtotal_amount,
                o.shipping_amount,
                o.discount_amount,
                o.total_amount,
                o.status,
                o.source_url,
                oi.external_item_id,
                oi.title_full,
                oi.title_short,
                oi.store_category_path,
                oi.unified_category_path,
                oi.brand,
                oi.model,
                oi.sku,
                oi.quantity,
                oi.unit_price,
                oi.discount_amount AS item_discount_amount,
                oi.shipping_amount AS item_shipping_amount,
                oi.total_amount AS item_total_amount,
                oi.product_url,
                oi.order_url,
                oi.receipt_url,
                oi.comment_user,
                (
                    SELECT group_concat(m.local_path_abs, ' | ')
                    FROM media m
                    WHERE m.related_item_id = oi.id
                ) AS media_paths,
                (
                    SELECT group_concat(m.source_url, ' | ')
                    FROM media m
                    WHERE m.related_item_id = oi.id
                ) AS media_urls
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            JOIN stores s ON s.id = o.store_id
            ORDER BY COALESCE(o.order_datetime, o.created_at) DESC, o.id DESC, oi.id ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def duplicate_diagnostics(self) -> dict[str, list[dict[str, Any]]]:
        order_dupes = self.connection.execute(
            """
            SELECT store_id, external_order_id, COUNT(*) AS cnt
            FROM orders
            WHERE external_order_id IS NOT NULL
            GROUP BY store_id, external_order_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        item_dupes = self.connection.execute(
            """
            SELECT order_id, title_full, quantity, unit_price, COUNT(*) AS cnt
            FROM order_items
            GROUP BY order_id, title_full, quantity, unit_price
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        return {
            "orders": [dict(row) for row in order_dupes],
            "items": [dict(row) for row in item_dupes],
        }

    def fetch_counts(self) -> dict[str, int]:
        tables = [
            "stores",
            "accounts",
            "orders",
            "order_items",
            "products",
            "product_attributes",
            "media",
            "reviews",
            "raw_messages",
            "sync_runs",
        ]
        counts: dict[str, int] = {}
        for table in tables:
            row = self.connection.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
            counts[table] = int(row["cnt"])
        return counts
