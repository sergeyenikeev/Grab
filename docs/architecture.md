# Архитектура

## Слои
- `core/`
  - `db`: миграции и репозиторий SQLite.
  - `dedupe`: стабильные ключи идемпотентности.
  - `normalize`: единые модели заказа/позиции/атрибутов.
  - `media`: скачивание и дедуп медиа.
  - `reviews`: хранение отзывов и лимит публичных (до 5).
  - `logging`: текстовый + JSON логи с `correlation_id`.
- `sources/`
  - `email_gmail`: официальный Gmail API.
  - `email_imap`: IMAP (mail.ru/yandex).
  - `ozon/wildberries/yamarket/...`: точки расширения под direct-интеграции.
- `parsers/`
  - парсер email-шаблонов + fallback.
- `services/`
  - orchestration синка, экспорт, doctor.
- `tests/`
  - unit + integration на фикстурах.

## Дедуп ключи
- Заказ:
  - основной: `hash(store + external_order_id)`
  - fallback: `hash(store + email_message_id)`
  - эвристика: `hash(store + order_date + total_amount)`
- Позиция:
  - основной: `hash(store + external_item_id)`
  - fallback: `hash(store + email_message_id + item_index)`
  - эвристика: `hash(store + sku + order_date + unit_price + quantity)`
- Все записи пишутся через `upsert`.

## Основные таблицы
- `stores`, `accounts`, `sellers`
- `orders`, `order_items`
- `products`, `product_attributes`
- `media`, `reviews`
- `raw_messages`, `raw_events`
- `sync_runs`, `audit_log`

## Идемпотентность обновлений
- Повторный sync не создает дублей из-за уникальных ключей + `ON CONFLICT`.
- Обновляемые поля (статус, суммы, ссылки, метаданные) перезаписываются только при наличии новых значений.
- `comment_user` хранится как пользовательское поле в `order_items` и не затирается автопарсером.
