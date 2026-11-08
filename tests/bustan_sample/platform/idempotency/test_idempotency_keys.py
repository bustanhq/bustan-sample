"""The contract of the IdempotencyKeys port. Each test runs on each adapter."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.database import Database
from bustan_sample.platform.idempotency import (
    IdempotencyKeys,
    InMemoryIdempotencyKeys,
    SqliteIdempotencyKeys,
)

from support.database import BACKENDS, memory_database, open_sqlite


@asynccontextmanager
async def _keys(backend: str, path: Path) -> AsyncGenerator[tuple[Database, IdempotencyKeys]]:
    if backend == "memory":
        database = memory_database()
        yield database, InMemoryIdempotencyKeys(database)
        return
    async with open_sqlite(path) as database:
        keys = SqliteIdempotencyKeys(database, FixedClock())
        await keys.on_module_init()
        yield database, keys


@pytest.mark.parametrize("backend", BACKENDS)
def test_only_the_first_add_of_a_key_returns_true(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _keys(backend, tmp_path / "test.db") as (_, keys):
            assert not await keys.contains("a")
            assert await keys.add("a")
            assert not await keys.add("a")
            assert await keys.contains("a")
            assert await keys.add("b")

    asyncio.run(scenario())


@pytest.mark.parametrize("backend", BACKENDS)
def test_a_key_rolls_back_with_its_transaction(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _keys(backend, tmp_path / "test.db") as (database, keys):
            with pytest.raises(ConnectionError):
                async with database.transaction():
                    assert await keys.add("a")
                    raise ConnectionError("the work failed")
            assert not await keys.contains("a")
            async with database.transaction():
                assert await keys.add("a")
            assert await keys.contains("a")

    asyncio.run(scenario())


def test_two_processes_on_one_file_add_a_key_one_time(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "shared.db"
        async with open_sqlite(path) as first_db, open_sqlite(path) as second_db:
            first = SqliteIdempotencyKeys(first_db, FixedClock())
            second = SqliteIdempotencyKeys(second_db, FixedClock())
            await first.on_module_init()
            await second.on_module_init()

            async def add(database: Database, keys: IdempotencyKeys) -> bool:
                async with database.transaction():
                    return await keys.add("tasks.starter_task:1")

            results = await asyncio.gather(add(first_db, first), add(second_db, second))
            assert sorted(results) == [False, True]

    asyncio.run(scenario())
