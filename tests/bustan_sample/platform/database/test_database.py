import asyncio
import sqlite3
from pathlib import Path

import pytest
from bustan import ConfigService

from bustan_sample.platform.database import Database, DatabaseBackend, Migration

from support.database import open_sqlite


def test_the_memory_backend_opens_no_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(ConfigService({"DATABASE_SQLITE_PATH": str(tmp_path / "x.db")}))
        await database.on_module_init()
        assert database.backend is DatabaseBackend.MEMORY
        assert not (tmp_path / "x.db").exists()
        with pytest.raises(RuntimeError, match="not open"):
            await database.execute("SELECT 1")

    asyncio.run(scenario())


def test_the_sqlite_backend_makes_the_folder_and_uses_wal(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "new-folder" / "app.db"
        async with open_sqlite(path) as database:
            row = await database.fetch_one("PRAGMA journal_mode")
            assert row is not None and row[0] == "wal"
        assert path.exists()

    asyncio.run(scenario())


def test_a_transaction_rolls_back_on_an_error(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "app.db") as database:
            await database.execute_script("CREATE TABLE notes (text TEXT)")
            with pytest.raises(ValueError):
                async with database.transaction() as connection:
                    await connection.execute("INSERT INTO notes VALUES ('lost')")
                    raise ValueError("stop")
            async with database.transaction() as connection:
                await connection.execute("INSERT INTO notes VALUES ('kept')")
            rows = await database.fetch_all("SELECT text FROM notes")
            assert [row["text"] for row in rows] == ["kept"]

    asyncio.run(scenario())


MIGRATIONS = (
    Migration(1, "create notes", "CREATE TABLE notes (text TEXT);"),
    Migration(2, "add a column", "ALTER TABLE notes ADD COLUMN author TEXT;"),
)


def test_migrate_applies_each_version_one_time(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "app.db") as database:
            assert await database.migrate("notes", MIGRATIONS[:1]) == [1]
            assert await database.migrate("notes", MIGRATIONS) == [2]
            assert await database.migrate("notes", MIGRATIONS) == []
            await database.execute("INSERT INTO notes (text, author) VALUES ('a', 'ada')")
            rows = await database.fetch_all(
                "SELECT version FROM schema_migrations WHERE component = 'notes'"
            )
            assert [row["version"] for row in rows] == [1, 2]

    asyncio.run(scenario())


def test_a_failed_migration_leaves_no_change(tmp_path: Path) -> None:
    async def scenario() -> None:
        broken = (Migration(1, "broken", "CREATE TABLE ok (x TEXT); SELECT * FROM missing;"),)
        async with open_sqlite(tmp_path / "app.db") as database:
            with pytest.raises(sqlite3.OperationalError):
                await database.migrate("broken", broken)
            tables = await database.fetch_all(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'ok'"
            )
            assert tables == []
            assert await database.migrate("broken", broken[:0]) == []

    asyncio.run(scenario())


def test_two_processes_that_migrate_together_apply_once(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "app.db"
        async with open_sqlite(path) as first, open_sqlite(path) as second:
            results = await asyncio.gather(
                first.migrate("notes", MIGRATIONS), second.migrate("notes", MIGRATIONS)
            )
        assert sorted(results[0] + results[1]) == [1, 2]

    asyncio.run(scenario())


def test_versions_must_go_up_from_one(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "app.db") as database:
            with pytest.raises(ValueError, match="unique"):
                await database.migrate("bad", (MIGRATIONS[1], MIGRATIONS[0]))

    asyncio.run(scenario())
