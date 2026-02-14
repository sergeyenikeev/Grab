from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from grab.config import Settings
from grab.core.db import GrabRepository
from grab.core.dedupe import (
    build_item_dedupe_key,
    build_order_dedupe_key,
    build_product_canonical_key,
)
from grab.core.media import MediaManager
from grab.parsers import parse_email_to_orders
from grab.sources.email_gmail import GmailAuthManager, GmailEmailSource
from grab.sources.email_imap import ImapEmailSource
from grab.sources.models import EmailMessageData

SOURCE_FILTER_MAP = {
    "all": None,
    "email": None,
    "ozon": "ozon",
    "wb": "wildberries",
    "wildberries": "wildberries",
    "yamarket": "yamarket",
    "megamarket": "megamarket",
    "dns": "dns",
    "auchan": "auchan",
}


class SyncService:
    def __init__(
        self,
        settings: Settings,
        repository: GrabRepository,
        logger: logging.Logger | logging.LoggerAdapter,
    ):
        self.settings = settings
        self.repository = repository
        self.logger = logger
        self.media_manager = MediaManager(repository=repository, media_root=settings.media_dir)

    @staticmethod
    def _to_iso(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    def _collect_email_messages(self, since: datetime | None = None) -> list[EmailMessageData]:
        messages: list[EmailMessageData] = []

        gmail_configured = (
            self.settings.gmail_client_secret_path.exists()
            or self.settings.gmail_token_path.exists()
        )
        if gmail_configured:
            try:
                auth_manager = GmailAuthManager(
                    client_secret_path=self.settings.gmail_client_secret_path,
                    token_path=self.settings.gmail_token_path,
                )
                gmail_source = GmailEmailSource(auth_manager=auth_manager, account=self.settings.gmail_account)
                gmail_messages = gmail_source.fetch_messages(
                    keywords=self.settings.email_keywords,
                    since=since,
                )
                messages.extend(gmail_messages)
                self.logger.info("Gmail messages collected: %s", len(gmail_messages))
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Gmail source skipped: %s", exc)
        else:
            self.logger.info("Gmail source skipped: OAuth files are not configured")

        for account in self.settings.imap_accounts:
            try:
                source = ImapEmailSource(account)
                imap_messages = source.fetch_messages(
                    keywords=self.settings.email_keywords,
                    since=since,
                )
                messages.extend(imap_messages)
                self.logger.info(
                    "IMAP messages collected from %s: %s", account.provider, len(imap_messages)
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("IMAP source %s skipped: %s", account.provider, exc)

        return messages

    def _store_filter(self, source: str) -> str | None:
        return SOURCE_FILTER_MAP.get(source)

    def sync(
        self,
        *,
        source: str,
        since: datetime | None,
        media_download: bool,
        correlation_id: str,
    ) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)
        self.repository.start_sync_run(correlation_id=correlation_id, source=source, started_at=started_at.isoformat())

        stats: dict[str, Any] = {
            "messages_total": 0,
            "messages_processed": 0,
            "orders_upserted": 0,
            "items_upserted": 0,
            "media_saved": 0,
            "errors": 0,
        }

        try:
            messages = self._collect_email_messages(since=since)
            stats["messages_total"] = len(messages)
            store_filter = self._store_filter(source)

            for message in messages:
                try:
                    account_identifier = message.account or "unknown"
                    account_id = self.repository.upsert_account(
                        provider=message.provider,
                        account_identifier=account_identifier,
                        display_name=account_identifier,
                    )

                    raw_message_id = self.repository.upsert_raw_message(
                        source=message.source,
                        account_id=account_id,
                        external_message_id=message.message_id,
                        thread_id=message.thread_id,
                        message_datetime=self._to_iso(message.sent_at),
                        subject=message.subject,
                        sender=message.sender,
                        recipients=", ".join(message.recipients),
                        raw_text=message.text_body,
                        raw_html=message.html_body,
                        raw_json=message.raw_payload,
                        raw_eml_path=None,
                    )

                    parsed_orders = parse_email_to_orders(message)
                    if not parsed_orders:
                        continue

                    for parsed_order in parsed_orders:
                        if store_filter and parsed_order.store_code != store_filter:
                            continue

                        store_id = self.repository.upsert_store(
                            code=parsed_order.store_code,
                            name=parsed_order.store_name,
                        )

                        seller_id = None
                        if parsed_order.seller_name:
                            seller_id = self.repository.upsert_seller(
                                store_id=store_id,
                                name=parsed_order.seller_name,
                                inn=parsed_order.seller_inn,
                                legal_entity=parsed_order.seller_legal_entity,
                            )

                        order_key = build_order_dedupe_key(
                            store_code=parsed_order.store_code,
                            external_order_id=parsed_order.external_order_id,
                            email_message_id=parsed_order.source_message_id,
                            order_date=parsed_order.order_datetime,
                            total_amount=parsed_order.total_amount,
                        )

                        order_id = self.repository.upsert_order(
                            store_id=store_id,
                            account_id=account_id,
                            seller_id=seller_id,
                            external_order_id=parsed_order.external_order_id,
                            dedupe_key=order_key,
                            order_datetime=self._to_iso(parsed_order.order_datetime),
                            paid_datetime=self._to_iso(parsed_order.paid_datetime),
                            delivered_datetime=self._to_iso(parsed_order.delivered_datetime),
                            currency=parsed_order.currency,
                            subtotal_amount=parsed_order.subtotal_amount,
                            shipping_amount=parsed_order.shipping_amount,
                            discount_amount=parsed_order.discount_amount,
                            total_amount=parsed_order.total_amount,
                            status=parsed_order.status,
                            source_url=parsed_order.source_url,
                            raw_ref=str(raw_message_id),
                        )
                        stats["orders_upserted"] += 1

                        item_ids: list[int] = []
                        order_ref = parsed_order.external_order_id or (
                            parsed_order.order_datetime.strftime("%Y-%m-%d")
                            if parsed_order.order_datetime
                            else "unknown_date"
                        )

                        for item_index, item in enumerate(parsed_order.items):
                            product_key = build_product_canonical_key(
                                brand=item.brand,
                                model=item.model,
                                sku=item.sku,
                                title=item.title_full,
                            )
                            product_id = self.repository.upsert_product(
                                canonical_key=product_key,
                                title_full=item.title_full,
                                title_short=item.title_short,
                                brand=item.brand,
                                model=item.model,
                                sku=item.sku,
                            )

                            item_key = build_item_dedupe_key(
                                store_code=parsed_order.store_code,
                                external_item_id=item.external_item_id,
                                email_message_id=parsed_order.source_message_id,
                                item_index=item_index,
                                sku=item.sku,
                                order_date=parsed_order.order_datetime,
                                unit_price=item.unit_price,
                                quantity=item.quantity,
                            )

                            item_id = self.repository.upsert_order_item(
                                order_id=order_id,
                                external_item_id=item.external_item_id,
                                dedupe_key=item_key,
                                product_id=product_id,
                                title_full=item.title_full,
                                title_short=item.title_short,
                                store_category_path=item.store_category_path,
                                unified_category_path=item.unified_category_path,
                                brand=item.brand,
                                model=item.model,
                                sku=item.sku,
                                quantity=item.quantity,
                                unit_price=item.unit_price,
                                discount_amount=item.discount_amount,
                                shipping_amount=item.shipping_amount,
                                total_amount=item.total_amount,
                                currency=item.currency or parsed_order.currency,
                                product_url=item.product_url,
                                order_url=item.order_url,
                                receipt_url=item.receipt_url,
                            )
                            item_ids.append(item_id)
                            stats["items_upserted"] += 1

                            for attribute in item.attributes:
                                self.repository.upsert_product_attribute(
                                    product_id=product_id,
                                    item_id=item_id,
                                    attr_key=attribute.key,
                                    value_type=attribute.value_type,
                                    value_text=attribute.value_text,
                                    value_number=attribute.value_number,
                                    value_bool=attribute.value_bool,
                                    value_json_raw=attribute.value_json_raw,
                                    source=attribute.source,
                                )

                            if media_download:
                                for media_url in item.media_urls:
                                    try:
                                        self.media_manager.download_from_url(
                                            store_code=parsed_order.store_code,
                                            order_ref=order_ref,
                                            item_id=item_id,
                                            url=media_url,
                                            source=f"{message.source}:link",
                                        )
                                        stats["media_saved"] += 1
                                    except Exception as exc:  # noqa: BLE001
                                        self.logger.warning(
                                            "Media link download failed for item %s: %s",
                                            item_id,
                                            exc,
                                        )

                        if media_download and item_ids:
                            target_item_id = item_ids[0]
                            for attachment in message.attachments:
                                try:
                                    self.media_manager.save_bytes(
                                        store_code=parsed_order.store_code,
                                        order_ref=order_ref,
                                        item_id=target_item_id,
                                        filename=attachment.filename,
                                        content=attachment.data,
                                        mime=attachment.content_type,
                                        source_url=attachment.source_url,
                                        source=f"{message.source}:attachment",
                                    )
                                    stats["media_saved"] += 1
                                except Exception as exc:  # noqa: BLE001
                                    self.logger.warning(
                                        "Attachment save failed for item %s: %s",
                                        target_item_id,
                                        exc,
                                    )

                    stats["messages_processed"] += 1
                except Exception as exc:  # noqa: BLE001
                    stats["errors"] += 1
                    self.logger.error("Message processing failed: %s", exc)

            self.repository.finish_sync_run(
                correlation_id=correlation_id,
                finished_at=datetime.now(timezone.utc).isoformat(),
                status="success" if stats["errors"] == 0 else "completed_with_errors",
                stats=stats,
                error_text=None,
            )
            return stats

        except Exception as exc:  # noqa: BLE001
            stats["errors"] += 1
            self.repository.finish_sync_run(
                correlation_id=correlation_id,
                finished_at=datetime.now(timezone.utc).isoformat(),
                status="failed",
                stats=stats,
                error_text=str(exc),
            )
            raise
