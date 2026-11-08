import asyncio
from pathlib import Path

import pytest
from bustan import ConfigService

from bustan_sample.platform.database import Database
from bustan_sample.platform.throttling import BackendThrottlerStorage

from support.database import BACKENDS, open_sqlite


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.parametrize("backend", BACKENDS)
def test_a_full_window_refuses_and_does_not_count_the_refusal(backend: str, tmp_path: Path) -> None:
    async def scenario() -> None:
        clock = _Clock()
        storage = BackendThrottlerStorage(clock)
        async with open_sqlite(tmp_path / "test.db") as sqlite:
            database = sqlite if backend == "sqlite" else Database(ConfigService({}))
            await storage.bind(database)
            states = [await storage.count_request("ip", ttl=60, limit=2) for _ in range(3)]
            assert [s.count for s in states] == [1, 2, 3]
            assert states[2].reset_after == 60
            clock.now += 30
            again = await storage.count_request("ip", ttl=60, limit=2)
            assert (again.count, again.reset_after) == (3, 30)
            clock.now += 31
            later = await storage.count_request("ip", ttl=60, limit=2)
            assert later.count == 1
            other = await storage.count_request("other-ip", ttl=60, limit=2)
            assert other.count == 1

    asyncio.run(scenario())


def test_two_processes_on_one_file_share_the_counts(tmp_path: Path) -> None:
    async def scenario() -> None:
        clock = _Clock()
        first, second = BackendThrottlerStorage(clock), BackendThrottlerStorage(clock)
        async with open_sqlite(tmp_path / "t.db") as one, open_sqlite(tmp_path / "t.db") as two:
            await first.bind(one)
            await second.bind(two)
            results = await asyncio.gather(
                *(storage.count_request("ip", ttl=60, limit=5) for storage in [first, second] * 4)
            )
        assert sorted(state.count for state in results) == [1, 2, 3, 4, 5, 6, 6, 6]

    asyncio.run(scenario())


def test_a_new_bind_starts_with_empty_memory_windows() -> None:
    async def scenario() -> None:
        storage = BackendThrottlerStorage(_Clock())
        memory = Database(ConfigService({}))
        await storage.bind(memory)
        await storage.count_request("ip", ttl=60, limit=1)
        await storage.bind(memory)
        assert (await storage.count_request("ip", ttl=60, limit=1)).count == 1

    asyncio.run(scenario())
