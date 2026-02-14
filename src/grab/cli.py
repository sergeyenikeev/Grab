from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer
from dateutil import parser as dt_parser
from rich import print

from grab.config import Settings
from grab.core.db import GrabRepository
from grab.core.logging import configure_logging, get_logger
from grab.services import SyncService, export_data, run_doctor_checks
from grab.sources.email_gmail import GmailAuthManager
from grab.sources.email_imap import ImapEmailSource

app = typer.Typer(no_args_is_help=True, help="Grab CLI: сбор и обновление истории покупок")


SOURCE_VALUES = [
    "all",
    "email",
    "ozon",
    "wb",
    "wildberries",
    "yamarket",
    "megamarket",
    "dns",
    "auchan",
    "aliexpress",
    "ali",
]


def _load_settings(base_dir: Path | None = None) -> Settings:
    settings = Settings.load(base_dir=base_dir)
    settings.ensure_directories()
    return settings


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = dt_parser.parse(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@app.command("init")
def init_command(
    base_dir: Path | None = typer.Option(None, help="Корень проекта (по умолчанию текущая папка)"),
) -> None:
    settings = _load_settings(base_dir=base_dir)
    with GrabRepository(settings.db_path) as repository:
        executed = repository.migrate()
    print(f"[green]Инициализация завершена[/green]. DB: {settings.db_path}")
    print(f"Миграции: {executed if executed else 'нет новых'}")


@app.command("auth")
def auth_command(
    gmail: bool = typer.Option(True, "--gmail/--no-gmail", help="Запустить OAuth для Gmail"),
    imap: bool = typer.Option(True, "--imap/--no-imap", help="Проверить IMAP (mail.ru/yandex)"),
) -> None:
    settings = _load_settings()

    if gmail:
        try:
            if not settings.gmail_client_secret_path.exists():
                raise FileNotFoundError(f"Нет файла Gmail client secret: {settings.gmail_client_secret_path}")
            # Быстрая проверка, что JSON валиден (учитываем BOM)
            with settings.gmail_client_secret_path.open("r", encoding="utf-8-sig") as fh:
                json.load(fh)

            manager = GmailAuthManager(settings.gmail_client_secret_path, settings.gmail_token_path)
            manager.ensure_credentials()
            print(f"[green]Gmail OAuth OK[/green]: {settings.gmail_token_path}")
        except Exception as exc:  # noqa: BLE001
            print(
                "[red]Gmail OAuth ошибка[/red]: "
                f"{exc.__class__.__name__}: {exc} (secret: {settings.gmail_client_secret_path})"
            )

    if imap:
        if not settings.imap_accounts:
            print("[yellow]IMAP аккаунты не настроены[/yellow]")
        for account in settings.imap_accounts:
            try:
                ImapEmailSource(account).check_connection()
                print(f"[green]IMAP OK[/green]: {account.provider} ({account.username}@{account.host}:{account.port})")
            except Exception as exc:  # noqa: BLE001
                print(
                    "[red]IMAP ошибка[/red] "
                    f"{account.provider} ({account.username}@{account.host}:{account.port}): "
                    f"{exc.__class__.__name__}: {exc}"
                )


@app.command("sync")
def sync_command(
    source: str = typer.Option("all", help=f"Источник: {', '.join(SOURCE_VALUES)}"),
    since: str | None = typer.Option(None, help="Дата/время с которой брать данные"),
    media: str = typer.Option("download", help="download|skip"),
    max_messages: int | None = typer.Option(
        None,
        help="Макс. писем на источник за один запуск (по умолчанию из GRAB_EMAIL_MAX_MESSAGES)",
    ),
) -> None:
    if source not in SOURCE_VALUES:
        raise typer.BadParameter(f"Недопустимый source: {source}")
    if media not in {"download", "skip"}:
        raise typer.BadParameter("Параметр --media должен быть download или skip")

    since_dt = _parse_since(since)
    correlation_id = uuid.uuid4().hex

    settings = _load_settings()
    max_messages_value = max_messages if max_messages is not None else settings.email_max_messages
    configure_logging(settings.logs_dir, correlation_id=correlation_id)
    logger = get_logger("grab.sync", correlation_id)

    with GrabRepository(settings.db_path) as repository:
        repository.migrate()
        service = SyncService(settings=settings, repository=repository, logger=logger)
        stats = service.sync(
            source=source,
            since=since_dt,
            media_download=media == "download",
            correlation_id=correlation_id,
            max_messages=max_messages_value,
        )

    print(f"[green]Sync завершен[/green]. correlation_id={correlation_id}")
    for key, value in stats.items():
        print(f"- {key}: {value}")


@app.command("export")
def export_command(
    format: str = typer.Option("xlsx,csv", help="Список форматов через запятую: xlsx,csv"),
    out: Path | None = typer.Option(None, help="Папка экспорта"),
) -> None:
    formats = [item.strip().lower() for item in format.split(",") if item.strip()]
    supported = {"xlsx", "csv"}
    unknown = [item for item in formats if item not in supported]
    if unknown:
        raise typer.BadParameter(f"Неподдерживаемые форматы: {unknown}")

    settings = _load_settings()
    out_dir = (out or settings.exports_dir).resolve()

    with GrabRepository(settings.db_path) as repository:
        repository.migrate()
        files = export_data(repository=repository, formats=formats, out_dir=out_dir)

    print("[green]Экспорт завершен[/green]")
    for file_path in files:
        print(f"- {file_path}")


@app.command("doctor")
def doctor_command() -> None:
    settings = _load_settings()
    checks = run_doctor_checks(settings)

    print("Результаты doctor:")
    for check in checks:
        status = check["status"].upper()
        print(f"- [{status}] {check['check']}: {check['detail']}")


@app.command("dedupe")
def dedupe_command() -> None:
    settings = _load_settings()
    with GrabRepository(settings.db_path) as repository:
        repository.migrate()
        diagnostics = repository.duplicate_diagnostics()

    print("Диагностика дублей:")
    print(f"- orders: {len(diagnostics['orders'])}")
    print(f"- items: {len(diagnostics['items'])}")


@app.command("tests")
def tests_command() -> None:
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], check=False)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
    print("[green]Тесты прошли успешно[/green]")


if __name__ == "__main__":
    app()
