from __future__ import annotations

from pathlib import Path

from grab.config import Settings


def test_settings_loads_multiple_yandex_accounts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAB_HOME", str(tmp_path))
    monkeypatch.setenv("YANDEX_IMAP_USER", "user1@yandex.ru")
    monkeypatch.setenv("YANDEX_IMAP_PASSWORD", "pass1")
    monkeypatch.setenv("YANDEX_IMAP_USER_2", "user2@yandex.ru")
    monkeypatch.setenv("YANDEX_IMAP_PASSWORD_2", "pass2")

    settings = Settings.load(base_dir=tmp_path)

    yandex_accounts = [a for a in settings.imap_accounts if a.provider == "yandex"]
    assert len(yandex_accounts) == 2
    assert yandex_accounts[0].username == "user1@yandex.ru"
    assert yandex_accounts[1].username == "user2@yandex.ru"
