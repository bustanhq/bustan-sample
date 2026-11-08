import asyncio
from pathlib import Path

import pytest
from bustan import ConfigService
from support.database import open_sqlite

from bustan_sample.platform.database import Database, DatabaseBackend


def test_the_memory_backend_opens_no_file(tmp_path: Path) -> None:
    async def scenario() -> None:
        database = Database(
            ConfigService({"DATABASE_SQLITE_PATH": str(tmp_path / "x.db")})
        )
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
