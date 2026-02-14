# Разработка

## Требования
- Python 3.11+
- Windows 11

## Установка
- `python -m venv .venv`
- `.\.venv\Scripts\activate`
- `pip install -r requirements-dev.txt`

## Полезные команды
- `grab init`
- `grab tests`
- `grab sync --source email --since 2025-01-01`
- `grab export --format xlsx,csv`

## Тестирование
- Unit: дедуп, парсеры, медиа-менеджер, upsert.
- Integration: end-to-end sync на фикстурах.
- Запуск: `pytest -q`

## Стиль
- Линтер: `ruff`.
- Изменения должны сохранять идемпотентность и обратимую миграцию схемы.
