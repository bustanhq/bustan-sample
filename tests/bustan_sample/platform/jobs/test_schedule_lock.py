"""The contract of the ScheduleLock port, and the shared SQLite lock."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.jobs import (
    InMemoryScheduleLock,
    ScheduleLock,
    SqliteScheduleLock,
)

from support.database import BACKENDS, open_sqlite

RUN = datetime(2026, 1, 1, 9, 10, tzinfo=UTC)


@asynccontextmanager
async def _lock(backend: str, path: Path) -> AsyncGenerator[ScheduleLock]:
    if backend == "memory":
        yield InMemoryScheduleLock()
        return
    async with open_sqlite(path) as database:
        lock = SqliteScheduleLock(database, FixedClock())
        await lock.on_module_init()
        yield lock


@pytest.mark.parametrize("backend", BACKENDS)
def test_each_run_is_claimed_one_time(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        async with _lock(backend, tmp_path / "test.db") as lock:
            assert await lock.claim("purge", RUN) is True
            assert await lock.claim("purge", RUN) is False
            assert await lock.claim("purge", RUN + timedelta(minutes=10)) is True
            assert await lock.claim("report", RUN) is True

    asyncio.run(scenario())


def test_two_processes_on_one_file_claim_a_run_one_time(tmp_path: Path) -> None:
    async def scenario() -> None:
        path = tmp_path / "test.db"
        async with open_sqlite(path) as first_db, open_sqlite(path) as second_db:
            first = SqliteScheduleLock(first_db, FixedClock())
            second = SqliteScheduleLock(second_db, FixedClock())
            await first.on_module_init()
            await second.on_module_init()
            results = await asyncio.gather(first.claim("purge", RUN), second.claim("purge", RUN))
        assert sorted(results) == [False, True]

    asyncio.run(scenario())
