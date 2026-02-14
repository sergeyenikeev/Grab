from __future__ import annotations

from datetime import datetime, timezone

from grab.services.sync import SyncService
from grab.sources.models import EmailMessageData


def test_sync_service_idempotent_on_duplicate_message(settings, repository, test_logger):  # noqa: ANN001
    service = SyncService(settings=settings, repository=repository, logger=test_logger)

    message = EmailMessageData(
        source="imap_mailru",
        provider="mailru",
        account="user@mail.ru",
        message_id="m-1",
        thread_id=None,
        subject="Ozon заказ №123456",
        sender="info@ozon.ru",
        recipients=["user@mail.ru"],
        sent_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        text_body="Заказ №123456\n- Товар А, 1 шт, 1000 ₽\nИтого: 1000 ₽",
        html_body=None,
        links=[],
        attachments=[],
        raw_payload={"fixture": True},
    )

    service._collect_email_messages = lambda since=None: [message, message]  # noqa: SLF001,E731

    stats = service.sync(
        source="email",
        since=None,
        media_download=False,
        correlation_id="sync-test-1",
    )

    assert stats["messages_total"] == 2
    assert repository.connection.execute("SELECT COUNT(*) AS cnt FROM orders").fetchone()["cnt"] == 1
    assert repository.connection.execute("SELECT COUNT(*) AS cnt FROM order_items").fetchone()["cnt"] == 1
