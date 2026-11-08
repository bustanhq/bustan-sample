import asyncio
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from bustan import ConfigService

from bustan_sample.platform.database import Database, DatabaseBackend, Migration

from support.database import BACKENDS, memory_database, open_sqlite


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
                async with database.transaction():
                    await database.execute("INSERT INTO notes VALUES ('lost')")
                    raise ValueError("stop")
            async with database.transaction():
                await database.execute("INSERT INTO notes VALUES ('kept')")
            rows = await database.fetch_all("SELECT text FROM notes")
            assert [row["text"] for row in rows] == ["kept"]

    asyncio.run(scenario())


def test_a_nested_transaction_joins_the_outer_one(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "app.db") as database:
            await database.execute_script("CREATE TABLE notes (text TEXT)")
            with pytest.raises(ValueError):
                async with database.transaction():
                    await database.execute("INSERT INTO notes VALUES ('outer')")
                    async with database.transaction():
                        await database.execute("INSERT INTO notes VALUES ('inner')")
                    assert database.in_transaction
                    raise ValueError("stop")
            assert not database.in_transaction
            assert await database.fetch_all("SELECT text FROM notes") == []

    asyncio.run(scenario())


@asynccontextmanager
async def _database(backend: str, path: Path) -> AsyncGenerator[Database]:
    if backend == "memory":
        yield memory_database()
        return
    async with open_sqlite(path) as database:
        yield database


@pytest.mark.parametrize("backend", BACKENDS)
def test_callbacks_run_after_the_commit_or_after_the_rollback(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _database(backend, tmp_path / "app.db") as database:
            calls: list[str] = []
            async with database.transaction():
                database.after_commit(lambda: calls.append("commit"))
                database.after_rollback(lambda: calls.append("rollback"))
                assert calls == []
            assert calls == ["commit"]
            calls.clear()
            with pytest.raises(ValueError):
                async with database.transaction():
                    database.after_commit(lambda: calls.append("commit"))
                    database.after_rollback(lambda: calls.append("rollback"))
                    raise ValueError("stop")
            assert calls == ["rollback"]
            calls.clear()
            database.after_commit(lambda: calls.append("no transaction"))
            database.after_rollback(lambda: calls.append("never"))
            assert calls == ["no transaction"]

    asyncio.run(scenario())


def test_a_failed_callback_does_not_stop_the_other_callbacks() -> None:
    async def scenario() -> None:
        database, calls = memory_database(), []

        def fail() -> None:
            raise RuntimeError("broken callback")

        async with database.transaction():
            database.after_commit(fail)
            database.after_commit(lambda: calls.append("second"))
        assert calls == ["second"]

    asyncio.run(scenario())


def test_a_task_that_a_transaction_starts_does_not_join_it(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "app.db") as database:
            await database.execute_script("CREATE TABLE notes (text TEXT)")

            async def count() -> int:
                row = await database.fetch_one("SELECT COUNT(*) FROM notes")
                assert row is not None
                return row[0]

            async with database.transaction():
                await database.execute("INSERT INTO notes VALUES ('a')")
                reader = asyncio.create_task(count())
                await asyncio.sleep(0.05)
                # The reader waits for the lock, thus it cannot see the open transaction.
                assert not reader.done()
            assert await reader == 1

    asyncio.run(scenario())


def test_a_schema_change_in_a_transaction_is_refused(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with open_sqlite(tmp_path / "app.db") as database, database.transaction():
            with pytest.raises(RuntimeError, match="transaction"):
                await database.execute_script("CREATE TABLE notes (text TEXT)")
            with pytest.raises(RuntimeError, match="transaction"):
                await database.migrate("notes", MIGRATIONS)

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
