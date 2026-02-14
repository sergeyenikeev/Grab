# Медиа

## Где хранятся
- Корень: `D:\p\Grab\data\media\`
- Структура позиции:
  - `D:\p\Grab\data\media\<store>\<order_id_or_date>\<item_id>\images\*`
  - `D:\p\Grab\data\media\<store>\<order_id_or_date>\<item_id>\videos\*`
  - `D:\p\Grab\data\media\<store>\<order_id_or_date>\<item_id>\meta.json`

## Что скачивается в MVP
- Вложения писем.
- Медиа-ссылки из писем (если URL ведет на изображение/видео).

## Дедупликация
- По `sha256` содержимого.
- Если файл уже есть, повторно не скачивается.
- Для новой позиции создается связь в БД (`media`) с уже существующим `local_path_abs`.

## Что записывается в БД
- `source_url`
- `local_path_abs` (абсолютный Windows путь)
- `mime`, `sha256`, `size_bytes`, `source`, `downloaded_at`

## meta.json
Для каждого media-объекта фиксируются:
- источник (`source`), исходный URL
- время скачивания
- `sha256`, `mime`, размер
- локальный абсолютный путь
