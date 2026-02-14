from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def apply_migrations(connection: sqlite3.Connection, migrations_dir: Path) -> list[str]:
    _ensure_migrations_table(connection)

    applied_files = {
        row["filename"] for row in connection.execute("SELECT filename FROM schema_migrations")
    }
    executed: list[str] = []

    for migration_file in sorted(migrations_dir.glob("*.sql")):
        if migration_file.name in applied_files:
            continue

        script = migration_file.read_text(encoding="utf-8")
        with connection:
            connection.executescript(script)
            connection.execute(
                "INSERT INTO schema_migrations (filename) VALUES (?)",
                (migration_file.name,),
            )
        executed.append(migration_file.name)

    return executed
