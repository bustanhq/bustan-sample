import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from support.database import open_sqlite, sqlite_config

from bustan_sample.platform.clock import FixedClock
from bustan_sample.platform.database import Database, to_text
from bustan_sample.platform.jobs import SqliteJobQueue


@dataclass(frozen=True)
class Work:
    value: int


def _queue(database: Database, path: Path, clock: FixedClock) -> SqliteJobQueue:
    config = sqlite_config(
        path,
        JOBS_WORKERS=2,
        JOBS_RETRY_DELAY_SECONDS=0,
        JOBS_POLL_SECONDS=0.01,
        JOBS_LEASE_SECONDS=60,
    )
    return SqliteJobQueue(database, config, clock)


@asynccontextmanager
async def _started(
    database: Database, path: Path, clock: FixedClock, handler, max_attempts: int = 3
) -> AsyncGenerator[SqliteJobQueue]:
    queue = _queue(database, path, clock)
    await queue.on_module_init()
    queue.register(Work, handler, max_attempts=max_attempts)
    await queue.on_application_bootstrap()
    try:
        yield queue
    finally:
        await queue.on_application_shutdown(None)


def test_an_enqueued_job_runs_and_leaves_the_table(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, done = tmp_path / "test.db", []

        async def handle(job: Work) -> None:
            done.append(job.value)

        async with open_sqlite(path) as database:
            async with _started(database, path, FixedClock(), handle) as queue:
                await queue.enqueue(Work(1))
                await queue.enqueue(Work(2))
                assert await queue.drain(2)
            rows = await database.fetch_all("SELECT * FROM jobs")
        assert sorted(done) == [1, 2]
        assert rows == []

    asyncio.run(scenario())


def test_a_failed_job_runs_again_and_is_kept_after_the_last_attempt(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        path, attempts = tmp_path / "test.db", []

        async def broken(job: Work) -> None:
            attempts.append(job.value)
            raise ConnectionError("the service is not available")

        async with (
            open_sqlite(path) as database,
            _started(database, path, FixedClock(), broken, 3) as queue,
        ):
            await queue.enqueue(Work(7))
            assert await queue.drain(2)
            [failed] = await queue.failed_jobs()
        assert attempts == [7, 7, 7]
        assert (failed.job, failed.attempts) == (Work(7), 3)
        assert "not available" in failed.error

    asyncio.run(scenario())


def test_a_queued_job_survives_a_restart(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, done = tmp_path / "test.db", []

        async def handle(job: Work) -> None:
            done.append(job.value)

        async with open_sqlite(path) as database:
            queue = _queue(database, path, FixedClock())
            await queue.on_module_init()
            queue.register(Work, handle)
            await queue.enqueue(Work(3))  # no worker runs in this "process"
        assert done == []
        async with (
            open_sqlite(path) as database,
            _started(database, path, FixedClock(), handle) as queue,
        ):
            assert await queue.drain(2)
        assert done == [3]

    asyncio.run(scenario())


def test_two_processes_on_one_file_run_each_job_one_time(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, done = tmp_path / "test.db", []

        async def handle(job: Work) -> None:
            await asyncio.sleep(0.001)
            done.append(job.value)

        clock = FixedClock()
        async with (
            open_sqlite(path) as first_db,
            open_sqlite(path) as second_db,
            _started(first_db, path, clock, handle) as first,
            _started(second_db, path, clock, handle) as second,
        ):
            for value in range(20):
                await first.enqueue(Work(value))
            assert await first.drain(5)
            assert await second.drain(5)
        assert sorted(done) == list(range(20))

    asyncio.run(scenario())


def test_a_job_of_a_stopped_process_runs_again_after_its_lease(tmp_path: Path) -> None:
    async def scenario() -> None:
        path, done, clock = tmp_path / "test.db", [], FixedClock()

        async def handle(job: Work) -> None:
            done.append(job.value)

        async with open_sqlite(path) as database:
            queue = _queue(database, path, clock)
            await queue.on_module_init()
            # A row that a process claimed, and did not end before it stopped.
            expired = to_text(clock.now() - timedelta(seconds=1))
            await database.execute(
                "INSERT INTO jobs (type, payload, attempt, status, run_after, "
                "locked_until, created_at) VALUES ('Work', '{\"value\": 9}', 1, "
                "'running', ?, ?, ?)",
                (expired, expired, expired),
            )
            async with _started(database, path, clock, handle) as started:
                assert await started.drain(2)
        assert done == [9]

    asyncio.run(scenario())
