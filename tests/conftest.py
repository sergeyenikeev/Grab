from __future__ import annotations

import logging
from pathlib import Path

import pytest

from grab.config import Settings
from grab.core.db import GrabRepository


@pytest.fixture()
def repository(tmp_path: Path):
    db_path = tmp_path / "grab.sqlite3"
    repo = GrabRepository(db_path)
    repo.migrate()
    try:
        yield repo
    finally:
        repo.close()


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    root = tmp_path / "project"
    root.mkdir(parents=True, exist_ok=True)
    s = Settings.load(base_dir=root)
    s.ensure_directories()
    return s


@pytest.fixture()
def test_logger() -> logging.Logger:
    logger = logging.getLogger("grab-test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.INFO)
    return logger
